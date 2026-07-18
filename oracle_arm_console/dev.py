import os

from .web import create_app


def main():
    create_app().run(
        debug=True,
        host=os.environ.get("WEB_HOST", "127.0.0.1"),
        port=int(os.environ.get("WEB_PORT", "8080")),
    )


if __name__ == "__main__":
    main()
