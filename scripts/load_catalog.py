"""Envoyer des appels concurrents au catalogue pour le test de limites Istio."""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def request(url):
    try:
        with urlopen(url, timeout=10) as response:
            response.read()
            return str(response.status)
    except HTTPError as error:
        error.close()
        return str(error.code)
    except (URLError, TimeoutError):
        return "erreur réseau"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:31380/countries")
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--workers", type=int, default=40)
    args = parser.parse_args()
    if args.requests < 1 or args.workers < 1:
        parser.error("--requests et --workers doivent être positifs")

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = Counter(pool.map(request, [args.url] * args.requests))

    for status, count in sorted(results.items()):
        print(f"{status} : {count}")


if __name__ == "__main__":
    main()
