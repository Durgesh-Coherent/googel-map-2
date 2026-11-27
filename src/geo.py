from __future__ import annotations

import re
from typing import Any

from .keyword_loader import slugify_country


# Country lock + geo filter settings for all supported markets.
COUNTRY_GEO: dict[str, dict[str, Any]] = {
    "uae": {
        "label": "UAE",
        "gl": "ae",
        "phone_prefixes": ("971",),
        "address_tokens": (
            "united arab emirates",
            " uae",
            "dubai",
            "abu dhabi",
            "sharjah",
            "ajman",
            "fujairah",
            "ras al khaimah",
            "al ain",
        ),
        "bounds": {"lat_min": 22.5, "lat_max": 26.5, "lng_min": 51.0, "lng_max": 56.6},
        "default_center": (25.2048, 55.2708),
        "cities": {
            "dubai": (25.2048, 55.2708),
            "abu dhabi": (24.4539, 54.3773),
            "sharjah": (25.3463, 55.4209),
            "ajman": (25.4052, 55.5136),
            "al ain": (24.1302, 55.8023),
            "ras al khaimah": (25.7895, 55.9432),
            "fujairah": (25.1288, 56.3269),
        },
    },
    "saudi_arabia": {
        "label": "Saudi Arabia",
        "gl": "sa",
        "phone_prefixes": ("966",),
        "address_tokens": (
            "saudi arabia",
            "ksa",
            "riyadh",
            "jeddah",
            "dammam",
            "khobar",
            "mecca",
            "medina",
            "jubail",
            "yanbu",
            "abha",
            "tabuk",
        ),
        "bounds": {"lat_min": 16.0, "lat_max": 32.5, "lng_min": 34.0, "lng_max": 56.0},
        "default_center": (24.7136, 46.6753),
        "cities": {
            "riyadh": (24.7136, 46.6753),
            "jeddah": (21.4858, 39.1925),
            "dammam": (26.4207, 50.0888),
            "khobar": (26.2172, 50.1971),
            "mecca": (21.3891, 39.8579),
            "medina": (24.5247, 39.5692),
            "jubail": (27.0046, 49.6614),
            "yanbu": (24.0895, 38.0618),
            "abha": (18.2164, 42.5053),
            "tabuk": (28.3838, 36.5550),
        },
    },
    "qatar": {
        "label": "Qatar",
        "gl": "qa",
        "phone_prefixes": ("974",),
        "address_tokens": (
            "qatar",
            "doha",
            "al rayyan",
            "al wakrah",
            "al khor",
            "lusail",
            "mesaieed",
            "ras laffan",
        ),
        "bounds": {"lat_min": 24.4, "lat_max": 26.3, "lng_min": 50.7, "lng_max": 51.7},
        "default_center": (25.2854, 51.5310),
        "cities": {
            "doha": (25.2854, 51.5310),
            "al rayyan": (25.2919, 51.4244),
            "al wakrah": (25.1715, 51.6034),
            "al khor": (25.6804, 51.4969),
            "lusail": (25.4358, 51.5010),
            "mesaieed": (24.9920, 51.5500),
            "ras laffan": (25.9100, 51.5400),
        },
    },
    "oman": {
        "label": "Oman",
        "gl": "om",
        "phone_prefixes": ("968",),
        "address_tokens": (
            "oman",
            "sultanate of oman",
            "muscat",
            "sohar",
            "salalah",
            "nizwa",
            "sur",
        ),
        "bounds": {"lat_min": 16.5, "lat_max": 26.5, "lng_min": 51.8, "lng_max": 59.9},
        "default_center": (23.5880, 58.3829),
        "cities": {
            "muscat": (23.5880, 58.3829),
            "sohar": (24.3450, 56.7080),
            "salalah": (17.0151, 54.0924),
            "nizwa": (22.9333, 57.5333),
            "sur": (22.5667, 59.5289),
        },
    },
    "kuwait": {
        "label": "Kuwait",
        "gl": "kw",
        "phone_prefixes": ("965",),
        "address_tokens": (
            "kuwait",
            "state of kuwait",
            "kuwait city",
            "al ahmadi",
            "ahmadi",
            "farwaniya",
            "hawalli",
            "jahra",
        ),
        "bounds": {"lat_min": 28.5, "lat_max": 30.1, "lng_min": 46.5, "lng_max": 48.6},
        "default_center": (29.3759, 47.9774),
        "cities": {
            "kuwait city": (29.3759, 47.9774),
            "al ahmadi": (29.0769, 48.0839),
            "farwaniya": (29.2977, 47.9391),
            "hawalli": (29.3328, 48.0263),
            "jahra": (29.3375, 47.6581),
        },
    },
    "italy": {
        "label": "Italy",
        "gl": "it",
        "phone_prefixes": ("39",),
        "address_tokens": (
            "italy",
            "italia",
            "milan",
            "milano",
            "bologna",
            "modena",
            "verona",
            "padova",
            "padua",
        ),
        "bounds": {"lat_min": 35.5, "lat_max": 47.1, "lng_min": 6.6, "lng_max": 18.5},
        "default_center": (45.4642, 9.1900),
        "cities": {
            "milan": (45.4642, 9.1900),
            "bologna": (44.4949, 11.3426),
            "modena": (44.6471, 10.9252),
            "verona": (45.4384, 10.9916),
            "padova": (45.4064, 11.8768),
        },
    },
    "france": {
        "label": "France",
        "gl": "fr",
        "phone_prefixes": ("33",),
        "address_tokens": (
            "france",
            "paris",
            "lyon",
            "toulouse",
            "rennes",
            "nantes",
        ),
        "bounds": {"lat_min": 41.0, "lat_max": 51.5, "lng_min": -5.5, "lng_max": 9.8},
        "default_center": (48.8566, 2.3522),
        "cities": {
            "paris": (48.8566, 2.3522),
            "lyon": (45.7640, 4.8357),
            "toulouse": (43.6047, 1.4442),
            "rennes": (48.1173, -1.6778),
            "nantes": (47.2184, -1.5536),
        },
    },
    "denmark": {
        "label": "Denmark",
        "gl": "dk",
        "phone_prefixes": ("45",),
        "address_tokens": (
            "denmark",
            "danmark",
            "copenhagen",
            "københavn",
            "kobenhavn",
            "aarhus",
            "odense",
            "aalborg",
            "esbjerg",
        ),
        "bounds": {"lat_min": 54.5, "lat_max": 57.8, "lng_min": 8.0, "lng_max": 15.2},
        "default_center": (55.6761, 12.5683),
        "cities": {
            "copenhagen": (55.6761, 12.5683),
            "aarhus": (56.1629, 10.2039),
            "odense": (55.4038, 10.4024),
            "aalborg": (57.0488, 9.9217),
            "esbjerg": (55.4765, 8.4594),
        },
    },
    "norway": {
        "label": "Norway",
        "gl": "no",
        "phone_prefixes": ("47",),
        "address_tokens": (
            "norway",
            "norge",
            "oslo",
            "bergen",
            "trondheim",
            "stavanger",
            "tromso",
            "tromsø",
        ),
        "bounds": {"lat_min": 57.9, "lat_max": 71.2, "lng_min": 4.5, "lng_max": 31.3},
        "default_center": (59.9139, 10.7522),
        "cities": {
            "oslo": (59.9139, 10.7522),
            "bergen": (60.3913, 5.3221),
            "trondheim": (63.4305, 10.3951),
            "stavanger": (58.9700, 5.7331),
            "tromso": (69.6492, 18.9553),
        },
    },
    "singapore": {
        "label": "Singapore",
        "gl": "sg",
        "phone_prefixes": ("65",),
        "address_tokens": ("singapore",),
        "bounds": {"lat_min": 1.16, "lat_max": 1.48, "lng_min": 103.6, "lng_max": 104.1},
        "default_center": (1.3521, 103.8198),
        "cities": {
            "singapore": (1.3521, 103.8198),
            "jurong": (1.3329, 103.7436),
        },
    },
    "spain": {
        "label": "Spain",
        "gl": "es",
        "phone_prefixes": ("34",),
        "address_tokens": (
            "spain",
            "españa",
            "espana",
            "madrid",
            "barcelona",
            "valencia",
            "zaragoza",
            "almeria",
            "almería",
        ),
        "bounds": {"lat_min": 36.0, "lat_max": 43.8, "lng_min": -9.3, "lng_max": 3.3},
        "default_center": (40.4168, -3.7038),
        "cities": {
            "madrid": (40.4168, -3.7038),
            "barcelona": (41.3851, 2.1734),
            "valencia": (39.4699, -0.3763),
            "zaragoza": (41.6488, -0.8891),
            "almeria": (36.8381, -2.4597),
        },
    },
    "netherlands": {
        "label": "Netherlands",
        "gl": "nl",
        "phone_prefixes": ("31",),
        "address_tokens": (
            "netherlands",
            "nederland",
            "holland",
            "amsterdam",
            "rotterdam",
            "the hague",
            "den haag",
            "westland",
            "eindhoven",
        ),
        "bounds": {"lat_min": 50.7, "lat_max": 53.6, "lng_min": 3.3, "lng_max": 7.3},
        "default_center": (52.3676, 4.9041),
        "cities": {
            "amsterdam": (52.3676, 4.9041),
            "rotterdam": (51.9244, 4.4777),
            "the hague": (52.0705, 4.3007),
            "westland": (52.0000, 4.2000),
            "eindhoven": (51.4416, 5.4697),
        },
    },
    "sweden": {
        "label": "Sweden",
        "gl": "se",
        "phone_prefixes": ("46",),
        "address_tokens": (
            "sweden",
            "sverige",
            "stockholm",
            "gothenburg",
            "göteborg",
            "goteborg",
            "malmo",
            "malmö",
            "uppsala",
            "orebro",
            "örebro",
        ),
        "bounds": {"lat_min": 55.0, "lat_max": 69.1, "lng_min": 10.9, "lng_max": 24.2},
        "default_center": (59.3293, 18.0686),
        "cities": {
            "stockholm": (59.3293, 18.0686),
            "gothenburg": (57.7089, 11.9746),
            "malmo": (55.6050, 13.0038),
            "uppsala": (59.8586, 17.6389),
            "orebro": (59.2741, 15.2066),
        },
    },
    "south_korea": {
        "label": "South Korea",
        "gl": "kr",
        "phone_prefixes": ("82",),
        "address_tokens": (
            "south korea",
            "korea",
            "seoul",
            "busan",
            "incheon",
            "daegu",
            "gwangju",
        ),
        "bounds": {"lat_min": 33.0, "lat_max": 38.9, "lng_min": 124.5, "lng_max": 130.0},
        "default_center": (37.5665, 126.9780),
        "cities": {
            "seoul": (37.5665, 126.9780),
            "busan": (35.1796, 129.0756),
            "incheon": (37.4563, 126.7052),
            "daegu": (35.8714, 128.6014),
            "gwangju": (35.1595, 126.8526),
        },
    },
    "japan": {
        "label": "Japan",
        "gl": "jp",
        "phone_prefixes": ("81",),
        "address_tokens": (
            "japan",
            "tokyo",
            "osaka",
            "nagoya",
            "sapporo",
            "fukuoka",
        ),
        "bounds": {"lat_min": 24.0, "lat_max": 45.7, "lng_min": 123.0, "lng_max": 146.0},
        "default_center": (35.6762, 139.6503),
        "cities": {
            "tokyo": (35.6762, 139.6503),
            "osaka": (34.6937, 135.5023),
            "nagoya": (35.1815, 136.9066),
            "sapporo": (43.0618, 141.3545),
            "fukuoka": (33.5904, 130.4017),
        },
    },
    "india": {
        "label": "India",
        "gl": "in",
        "phone_prefixes": ("91",),
        "address_tokens": (
            "india",
            "tamil nadu",
            "kerala",
            "andhra pradesh",
            "karnataka",
            "pollachi",
            "coimbatore",
            "udumalpet",
            "dharapuram",
            "tirupur",
            "tiruppur",
            "dindigul",
            "theni",
            "madurai",
            "tuticorin",
            "thoothukudi",
            "nagercoil",
            "chennai",
            "alappuzha",
            "alleppey",
            "kochi",
            "cochin",
            "ernakulam",
            "kollam",
            "thrissur",
            "kozhikode",
            "amalapuram",
            "rajahmundry",
            "vijayawada",
            "visakhapatnam",
            "tiptur",
            "hassan",
            "mangalore",
            "mangaluru",
            "bangalore",
            "bengaluru",
        ),
        "bounds": {"lat_min": 6.5, "lat_max": 37.1, "lng_min": 68.1, "lng_max": 97.4},
        "default_center": (13.0827, 80.2707),
        "cities": {
            "pollachi": (10.6586, 77.0085),
            "coimbatore": (11.0168, 76.9558),
            "udumalpet": (10.5872, 77.2487),
            "dharapuram": (10.7381, 77.5203),
            "tirupur": (11.1085, 77.3411),
            "dindigul": (10.3624, 77.9695),
            "theni": (10.0104, 77.4768),
            "madurai": (9.9252, 78.1198),
            "tuticorin": (8.7642, 78.1348),
            "nagercoil": (8.1833, 77.4119),
            "chennai": (13.0827, 80.2707),
            "alappuzha": (9.4981, 76.3388),
            "kochi": (9.9312, 76.2673),
            "kollam": (8.8932, 76.6141),
            "thrissur": (10.5276, 76.2144),
            "kozhikode": (11.2588, 75.7804),
            "amalapuram": (16.5783, 82.0060),
            "rajahmundry": (17.0005, 81.8040),
            "vijayawada": (16.5062, 80.6480),
            "visakhapatnam": (17.6868, 83.2185),
            "tiptur": (13.2560, 76.4774),
            "hassan": (13.0072, 76.0962),
            "mangalore": (12.9141, 74.8560),
            "bangalore": (12.9716, 77.5946),
        },
    },
    "algeria": {
        "label": "Algeria",
        "gl": "dz",
        "phone_prefixes": ("213",),
        "address_tokens": (
            "algeria",
            "algérie",
            "algerie",
            "algiers",
            "alger",
            "oran",
            "constantine",
            "setif",
            "sétif",
            "annaba",
            "blida",
            "batna",
            "tlemcen",
        ),
        "bounds": {"lat_min": 19.0, "lat_max": 37.1, "lng_min": -8.7, "lng_max": 12.0},
        "default_center": (36.7538, 3.0588),
        "cities": {
            "algiers": (36.7538, 3.0588),
            "oran": (35.6969, -0.6331),
            "constantine": (36.3650, 6.6147),
            "setif": (36.1898, 5.4108),
            "annaba": (36.9000, 7.7667),
        },
    },
    "ethiopia": {
        "label": "Ethiopia",
        "gl": "et",
        "phone_prefixes": ("251",),
        "address_tokens": (
            "ethiopia",
            "addis ababa",
            "bahir dar",
            "hawassa",
            "jimma",
            "dire dawa",
            "adama",
            "mekelle",
            "gondar",
        ),
        "bounds": {"lat_min": 3.4, "lat_max": 14.9, "lng_min": 33.0, "lng_max": 48.0},
        "default_center": (9.0250, 38.7469),
        "cities": {
            "addis ababa": (9.0250, 38.7469),
            "bahir dar": (11.5742, 37.3614),
            "hawassa": (7.0621, 38.4763),
            "jimma": (7.6733, 36.8340),
            "dire dawa": (9.5931, 41.8661),
        },
    },
    "tanzania": {
        "label": "Tanzania",
        "gl": "tz",
        "phone_prefixes": ("255",),
        "address_tokens": (
            "tanzania",
            "dar es salaam",
            "arusha",
            "mwanza",
            "morogoro",
            "dodoma",
            "mbeya",
            "tanga",
            "zanzibar",
        ),
        "bounds": {"lat_min": -11.8, "lat_max": -1.0, "lng_min": 29.3, "lng_max": 40.5},
        "default_center": (-6.7924, 39.2083),
        "cities": {
            "dar es salaam": (-6.7924, 39.2083),
            "arusha": (-3.3869, 36.6830),
            "mwanza": (-2.5164, 32.9175),
            "morogoro": (-6.8235, 37.6615),
            "dodoma": (-6.1630, 35.7516),
        },
    },
    "cote_divoire": {
        "label": "Cote d'Ivoire",
        "gl": "ci",
        "phone_prefixes": ("225",),
        "address_tokens": (
            "cote d'ivoire",
            "côte d'ivoire",
            "ivory coast",
            "abidjan",
            "san pedro",
            "bouake",
            "bouaké",
            "yamoussoukro",
            "korhogo",
            "daloa",
            "man",
        ),
        "bounds": {"lat_min": 4.3, "lat_max": 10.7, "lng_min": -8.6, "lng_max": -2.5},
        "default_center": (5.3600, -4.0083),
        "cities": {
            "abidjan": (5.3600, -4.0083),
            "san pedro": (4.7485, -6.6363),
            "bouake": (7.6939, -5.0308),
            "yamoussoukro": (6.8276, -5.2893),
            "korhogo": (9.4580, -5.6295),
        },
    },
    "mali": {
        "label": "Mali",
        "gl": "ml",
        "phone_prefixes": ("223",),
        "address_tokens": (
            "mali",
            "bamako",
            "segou",
            "ségou",
            "sikasso",
            "mopti",
            "koutiala",
            "kayes",
            "gao",
            "timbuktu",
        ),
        "bounds": {"lat_min": 10.1, "lat_max": 25.0, "lng_min": -12.2, "lng_max": 4.3},
        "default_center": (12.6392, -8.0029),
        "cities": {
            "bamako": (12.6392, -8.0029),
            "segou": (13.4317, -5.6744),
            "sikasso": (11.3175, -5.6664),
            "mopti": (14.4843, -4.1870),
            "koutiala": (12.3927, -5.4620),
        },
    },
    "ghana": {
        "label": "Ghana",
        "gl": "gh",
        "phone_prefixes": ("233",),
        "address_tokens": (
            "ghana",
            "accra",
            "kumasi",
            "tamale",
            "tema",
            "takoradi",
            "cape coast",
            "ho",
            "sunyani",
            "koforidua",
        ),
        "bounds": {"lat_min": 4.7, "lat_max": 11.2, "lng_min": -3.3, "lng_max": 1.2},
        "default_center": (5.6037, -0.1870),
        "cities": {
            "accra": (5.6037, -0.1870),
            "kumasi": (6.6885, -1.6244),
            "tamale": (9.4008, -0.8393),
            "tema": (5.6698, -0.0166),
            "takoradi": (4.8982, -1.7554),
        },
    },
    "gambia": {
        "label": "The Gambia",
        "gl": "gm",
        "phone_prefixes": ("220",),
        "address_tokens": (
            "gambia",
            "the gambia",
            "banjul",
            "serrekunda",
            "brikama",
            "basse santa su",
            "basse",
            "farafenni",
        ),
        "bounds": {"lat_min": 13.0, "lat_max": 13.8, "lng_min": -16.8, "lng_max": -13.8},
        "default_center": (13.4549, -16.5790),
        "cities": {
            "banjul": (13.4549, -16.5790),
            "serrekunda": (13.4397, -16.6775),
            "brikama": (13.2714, -16.6503),
            "basse santa su": (13.3103, -14.6530),
            "farafenni": (13.5667, -15.6000),
        },
    },
    "uganda": {
        "label": "Uganda",
        "gl": "ug",
        "phone_prefixes": ("256",),
        "address_tokens": (
            "uganda",
            "kampala",
            "jinja",
            "mbale",
            "mbarara",
            "masaka",
            "gulu",
            "entebbe",
            "fort portal",
        ),
        "bounds": {"lat_min": -1.5, "lat_max": 4.2, "lng_min": 29.6, "lng_max": 35.0},
        "default_center": (0.3476, 32.5825),
        "cities": {
            "kampala": (0.3476, 32.5825),
            "jinja": (0.4244, 33.2041),
            "mbale": (1.0647, 34.1797),
            "mbarara": (-0.6133, 30.6585),
            "masaka": (-0.3413, 31.7350),
        },
    },
    "guinea_bissau": {
        "label": "Guinea-Bissau",
        "gl": "gw",
        "phone_prefixes": ("245",),
        "address_tokens": (
            "guinea-bissau",
            "guinea bissau",
            "guiné-bissau",
            "bissau",
            "bafata",
            "bafatá",
            "gabu",
            "gabú",
            "cacheu",
            "bissora",
            "bissorã",
        ),
        "bounds": {"lat_min": 10.9, "lat_max": 12.7, "lng_min": -16.7, "lng_max": -13.6},
        "default_center": (11.8637, -15.5977),
        "cities": {
            "bissau": (11.8637, -15.5977),
            "bafata": (12.1725, -14.6586),
            "gabu": (12.2833, -14.2167),
            "cacheu": (12.2744, -16.1650),
            "bissora": (12.2231, -15.4486),
        },
    },
    "sudan": {
        "label": "Sudan",
        "gl": "sd",
        "phone_prefixes": ("249",),
        "address_tokens": (
            "sudan",
            "khartoum",
            "wad madani",
            "port sudan",
            "kassala",
            "el obeid",
            "al-obeid",
            "omdurman",
            "gezira",
            "al jazirah",
        ),
        "bounds": {"lat_min": 8.7, "lat_max": 22.2, "lng_min": 21.8, "lng_max": 38.6},
        "default_center": (15.5007, 32.5599),
        "cities": {
            "khartoum": (15.5007, 32.5599),
            "wad madani": (14.4004, 33.5197),
            "port sudan": (19.6158, 37.2164),
            "kassala": (15.4517, 36.3998),
            "el obeid": (13.1833, 30.2167),
        },
    },
    "nigeria": {
        "label": "Nigeria",
        "gl": "ng",
        "phone_prefixes": ("234",),
        "address_tokens": (
            "nigeria",
            "lagos",
            "kano",
            "kaduna",
            "ibadan",
            "port harcourt",
            "abuja",
            "onitsha",
            "benin city",
            "enugu",
            "oshogbo",
            "abeokuta",
            "jos",
            "ilorin",
            "warri",
            "aba",
        ),
        "bounds": {"lat_min": 4.2, "lat_max": 13.9, "lng_min": 2.7, "lng_max": 14.7},
        "default_center": (6.5244, 3.3792),
        "cities": {
            "lagos": (6.5244, 3.3792),
            "kano": (12.0022, 8.5920),
            "kaduna": (10.5105, 7.4165),
            "ibadan": (7.3775, 3.9470),
            "port harcourt": (4.8156, 7.0498),
        },
    },
    "egypt": {
        "label": "Egypt",
        "gl": "eg",
        "phone_prefixes": ("20",),
        "address_tokens": (
            "egypt",
            "مصر",
            "cairo",
            "alexandria",
            "giza",
            "mansoura",
            "tanta",
            "ismailia",
            "port said",
            "suez",
            "luxor",
            "aswan",
            "fayoum",
            "minya",
            "asyut",
            "zagazig",
            "damanhur",
        ),
        "bounds": {"lat_min": 22.0, "lat_max": 31.7, "lng_min": 24.7, "lng_max": 36.9},
        "default_center": (30.0444, 31.2357),
        "cities": {
            "cairo": (30.0444, 31.2357),
            "alexandria": (31.2001, 29.9187),
            "giza": (30.0131, 31.2089),
            "mansoura": (31.0409, 31.3785),
            "tanta": (30.7865, 31.0004),
        },
    },
    "south_africa": {
        "label": "South Africa",
        "gl": "za",
        "phone_prefixes": ("27",),
        "address_tokens": (
            "south africa",
            "johannesburg",
            "cape town",
            "durban",
            "pretoria",
            "stellenbosch",
            "bloemfontein",
            "port elizabeth",
            "gqeberha",
            "pietermaritzburg",
            "polokwane",
            "nelspruit",
            "mbombela",
            "east london",
            "rustenburg",
            "kimberley",
        ),
        "bounds": {"lat_min": -35.0, "lat_max": -22.0, "lng_min": 16.4, "lng_max": 33.0},
        "default_center": (-26.2041, 28.0473),
        "cities": {
            "johannesburg": (-26.2041, 28.0473),
            "cape town": (-33.9249, 18.4241),
            "durban": (-29.8587, 31.0218),
            "pretoria": (-25.7479, 28.2293),
            "stellenbosch": (-33.9321, 18.8602),
        },
    },
    "israel": {
        "label": "Israel",
        "gl": "il",
        "phone_prefixes": ("972",),
        "address_tokens": (
            "israel",
            "tel aviv",
            "tel aviv-yafo",
            "haifa",
            "jerusalem",
            "petah tikva",
            "beersheba",
            "beer sheva",
            "ashdod",
            "netanya",
            "herzliya",
            "holon",
            "rishon lezion",
            "rishon le zion",
        ),
        "bounds": {"lat_min": 29.4, "lat_max": 33.4, "lng_min": 34.2, "lng_max": 35.95},
        "default_center": (32.0853, 34.7818),
        "cities": {
            "tel aviv": (32.0853, 34.7818),
            "haifa": (32.7940, 34.9896),
            "jerusalem": (31.7683, 35.2137),
            "petah tikva": (32.0840, 34.8878),
            "beersheba": (31.2530, 34.7915),
            "ashdod": (31.8044, 34.6553),
            "netanya": (32.3215, 34.8532),
            "herzliya": (32.1624, 34.8447),
            "holon": (32.0156, 34.7874),
            "rishon lezion": (31.9730, 34.7925),
        },
    },
}


def get_country_geo(country: str) -> dict[str, Any] | None:
    slug = slugify_country(country)
    aliases = {
        "ksa": "saudi_arabia",
        "saudi": "saudi_arabia",
        "united_arab_emirates": "uae",
        "il": "israel",
        "ae": "uae",
        "sa": "saudi_arabia",
        "qa": "qatar",
        "eg": "egypt",
        "za": "south_africa",
        "rsa": "south_africa",
        "ng": "nigeria",
        "dz": "algeria",
        "et": "ethiopia",
        "tz": "tanzania",
        "ci": "cote_divoire",
        "ivory_coast": "cote_divoire",
        "cote_d_ivoire": "cote_divoire",
        "ml": "mali",
        "gh": "ghana",
        "gm": "gambia",
        "the_gambia": "gambia",
        "ug": "uganda",
        "gw": "guinea_bissau",
        "sd": "sudan",
    }
    slug = aliases.get(slug, slug)
    return COUNTRY_GEO.get(slug)


def city_center(country: str, city: str) -> tuple[float, float]:
    geo = get_country_geo(country)
    if not geo:
        return (0.0, 0.0)
    city_key = (city or "").strip().lower()
    cities: dict[str, tuple[float, float]] = geo.get("cities", {})
    if city_key in cities:
        return cities[city_key]
    for name, coords in cities.items():
        if name in city_key or city_key in name:
            return coords
    return tuple(geo["default_center"])


def normalize_phone_digits(phone: str | None) -> str:
    return re.sub(r"\D+", "", phone or "")


def matches_country(company: dict[str, Any], country: str) -> tuple[bool, str]:
    """Return whether company belongs to target country, plus reason."""
    geo = get_country_geo(country)
    if not geo:
        return True, "no_geo_config"

    lat = _to_float(company.get("latitude"))
    lng = _to_float(company.get("longitude"))
    bounds = geo["bounds"]
    in_bounds = False
    if lat is not None and lng is not None:
        in_bounds = (
            bounds["lat_min"] <= lat <= bounds["lat_max"]
            and bounds["lng_min"] <= lng <= bounds["lng_max"]
        )
        if in_bounds:
            return True, "coords"

    phone_digits = normalize_phone_digits(company.get("phone"))
    phone_ok = any(
        phone_digits.startswith(prefix) or phone_digits.startswith("0" + prefix)
        for prefix in geo["phone_prefixes"]
        if phone_digits
    )
    if phone_ok:
        return True, "phone"

    address = (
        f"{company.get('full_address') or ''} "
        f"{company.get('city') or ''} "
        f"{company.get('country') or ''}"
    ).lower()
    address_ok = any(token in address for token in geo["address_tokens"])
    if address_ok and (lat is None or lng is None or in_bounds):
        return True, "address"

    if lat is not None and lng is not None and not in_bounds:
        return False, f"coords_outside:{lat},{lng}"

    if phone_digits and not phone_ok:
        return False, f"phone_mismatch:{company.get('phone')}"

    if address.strip() and not address_ok:
        return False, "address_mismatch"

    if not phone_digits and not (company.get("full_address") or "").strip() and lat is None:
        return True, "insufficient_signals"

    return False, "no_country_match"


def url_outside_country(url: str, country: str) -> tuple[bool, str]:
    """
    Early reject using coordinates embedded in a Maps place URL.
    Returns (True, reason) only when coords are clearly outside the country.
    If coords are missing/unknown, returns (False, '') so caller can open the page.
    """
    geo = get_country_geo(country)
    if not geo:
        return False, ""

    lat_s, lng_s = extract_place_coords_from_url(url)
    lat = _to_float(lat_s)
    lng = _to_float(lng_s)
    if lat is None or lng is None:
        return False, ""

    bounds = geo["bounds"]
    inside = (
        bounds["lat_min"] <= lat <= bounds["lat_max"]
        and bounds["lng_min"] <= lng <= bounds["lng_max"]
    )
    if inside:
        return False, ""
    return True, f"url_coords_outside:{lat},{lng}"


def extract_place_coords_from_url(url: str) -> tuple[str, str]:
    # Prefer place marker coords over map viewport (@lat,lng).
    d_match = re.search(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)", url)
    if d_match:
        return d_match.group(1), d_match.group(2)
    if "/maps/place/" in url:
        at_match = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", url)
        if at_match:
            return at_match.group(1), at_match.group(2)
    return "", ""


def _to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
