import os

import oci

from .i18n import t


def load_oci_resources(settings):
    config_path = os.path.expanduser(settings.oci_config_file)
    config = oci.config.from_file(config_path, settings.oci_profile)
    oci.config.validate_config(config)

    identity = oci.identity.IdentityClient(config)
    compute = oci.core.ComputeClient(config)
    network = oci.core.VirtualNetworkClient(config)
    block_storage = oci.core.BlockstorageClient(config)
    tenancy = identity.get_tenancy(config["tenancy"]).data

    compartments = [{"id": tenancy.id, "name": t("errors.root_compartment", name=tenancy.name)}]
    children = oci.pagination.list_call_get_all_results(
        identity.list_compartments,
        compartment_id=tenancy.id,
        compartment_id_in_subtree=True,
        access_level="ACCESSIBLE",
        lifecycle_state="ACTIVE",
    ).data
    compartments.extend(
        {"id": item.id, "name": item.name}
        for item in sorted(children, key=lambda item: item.name.lower())
    )

    availability_domains = [
        {"name": item.name} for item in identity.list_availability_domains(tenancy.id).data
    ]

    subnets = []
    for compartment in compartments:
        try:
            items = oci.pagination.list_call_get_all_results(
                network.list_subnets,
                compartment_id=compartment["id"],
                lifecycle_state="AVAILABLE",
            ).data
        except oci.exceptions.ServiceError as exc:
            if exc.status in {401, 403, 404}:
                continue
            raise
        subnets.extend(
            {
                "id": item.id,
                "name": item.display_name,
                "compartment_name": compartment["name"],
                "availability_domain": item.availability_domain,
            }
            for item in items
            if not item.prohibit_public_ip_on_vnic
        )
    subnets.sort(key=lambda item: (item["compartment_name"].lower(), item["name"].lower()))

    images = oci.pagination.list_call_get_all_results(
        compute.list_images,
        compartment_id=tenancy.id,
        shape="VM.Standard.A1.Flex",
        lifecycle_state="AVAILABLE",
        sort_by="TIMECREATED",
        sort_order="DESC",
    ).data
    latest_images = []
    seen = set()
    for image in images:
        key = (image.operating_system, image.operating_system_version)
        if key in seen:
            continue
        seen.add(key)
        latest_images.append(
            {
                "id": image.id,
                "name": image.display_name,
                "operating_system": image.operating_system,
                "version": image.operating_system_version,
            }
        )
        if len(latest_images) >= 30:
            break

    volume_sizes = {}
    for compartment in compartments:
        try:
            volumes = oci.pagination.list_call_get_all_results(
                block_storage.list_volumes,
                compartment_id=compartment["id"],
            ).data
            for volume in volumes:
                if volume.lifecycle_state not in {"TERMINATED", "TERMINATING"}:
                    volume_sizes[volume.id] = float(volume.size_in_gbs or 0)
            for availability_domain in availability_domains:
                boot_volumes = oci.pagination.list_call_get_all_results(
                    block_storage.list_boot_volumes,
                    compartment_id=compartment["id"],
                    availability_domain=availability_domain["name"],
                ).data
                for volume in boot_volumes:
                    if volume.lifecycle_state not in {"TERMINATED", "TERMINATING"}:
                        volume_sizes[volume.id] = float(volume.size_in_gbs or 0)
        except oci.exceptions.ServiceError as exc:
            if exc.status in {401, 403, 404}:
                continue
            raise

    free_storage_total = 200.0
    used_storage = sum(volume_sizes.values())
    available_storage = max(0.0, free_storage_total - used_storage)

    return {
        "region": config["region"],
        "compartments": compartments,
        "availability_domains": availability_domains,
        "subnets": subnets,
        "images": latest_images,
        "storage": {
            "total_gb": free_storage_total,
            "used_gb": used_storage,
            "available_gb": available_storage,
            "minimum_boot_volume_gb": 50.0,
        },
    }
