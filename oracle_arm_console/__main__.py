import os

from waitress import serve

from .web import create_app


def main():
    serve(
        create_app(),
        host=os.environ.get("WEB_HOST", "127.0.0.1"),
        port=int(os.environ.get("WEB_PORT", "8080")),
        threads=int(os.environ.get("WEB_THREADS", "4")),
    )


if __name__ == "__main__":
    main()
