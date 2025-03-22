http_scheme = ["http", "https"]

domains = ["sanbjur.de"]

localhost = [
    "localhost:5174",
    "localhost:5173",
    "localhost:4173",
    "localhost:4174",
    "localhost:3000",
]

origins_without_scheme = [*localhost, *domains]


def add_scheme(origins, schemes=http_scheme):
    array = []
    for origin in origins:
        for scheme in schemes:
            array.append(f"{scheme}://{origin}")
    return array


allow_origins = [*add_scheme(localhost), *add_scheme(domains)]
