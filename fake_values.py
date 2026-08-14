"""
fake_values.py
--------------
Generates realistic-looking, deterministic replacement values for each PII
category. "Deterministic" means the same original value always maps to the
same fake value within a run (e.g. every occurrence of "Rohan Dey" becomes
the same "Peter Parker" everywhere in the document) -- mirroring the example
in the assignment brief.
"""

import hashlib
import random
import re

FIRST_NAMES = ["John", "Peter", "Alex", "Sam", "Chris", "Jordan", "Taylor",
                "Morgan", "Priya", "Rahul", "Anjali", "Vikram", "Neha", "Karan"]
LAST_NAMES = ["Doe", "Parker", "Smith", "Johnson", "Sharma", "Mehta", "Rao",
              "Iyer", "Kapoor", "Bose", "Nair", "Gupta", "Reddy", "Verma"]
COMPANY_WORDS = ["Acme", "Globex", "Initech", "Umbrella", "Stark", "Wayne",
                  "Hooli", "Wonka", "Cyberdyne", "Soylent"]
COMPANY_SUFFIXES = ["Private Limited", "Limited", "LLP", "Inc.", "Corporation"]
STREETS = ["Maple Street", "Oak Avenue", "Elm Road", "Sunset Boulevard",
           "MG Road", "Park Lane", "Industrial Estate Road"]
CITIES = [("Springfield", "State", "560001"), ("Rivertown", "State", "411001"),
          ("Lakeview", "State", "400001")]


class FakeValueFactory:
    """Holds the original -> fake mapping for one redaction run."""

    def __init__(self):
        self._map = {}
        self._used = set()

    def _get_rng(self, key):
        seed_val = int(hashlib.md5(key.encode('utf-8')).hexdigest(), 16)
        return random.Random(seed_val)

    # ---- helpers -----------------------------------------------------
    def _cache(self, key, category, builder):
        cache_key = (category, key.lower().strip())
        if cache_key in self._map:
            return self._map[cache_key]
            
        attempt = 0
        while True:
            seed_str = key if attempt == 0 else f"{key}_{attempt}"
            rng = self._get_rng(seed_str)
            candidate = builder(rng)
            if attempt > 50:
                candidate = f"{candidate} {attempt}"
            if candidate not in self._used:
                self._map[cache_key] = candidate
                self._used.add(candidate)
                return candidate
            attempt += 1

    # ---- per-category fakers -----------------------------------------
    def fake_name(self, original):
        def build(rng):
            return f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        return self._cache(original, "PERSON_NAME", build)

    def fake_email(self, original):
        def build(rng):
            f = rng.choice(FIRST_NAMES).lower()
            l = rng.choice(LAST_NAMES).lower()
            n = rng.randint(1, 999)
            return f"{f}.{l}{n}@example.com"
        return self._cache(original, "EMAIL", build)

    def fake_phone(self, original):
        def build(rng):
            digits = str(rng.randint(1000000000, 9999999999))
            prefix_match = re.match(r"^\+\d{1,3}", original.strip())
            prefix = prefix_match.group() if prefix_match else ""
            return f"{prefix} {digits}".strip() if prefix else digits
        return self._cache(original, "PHONE", build)

    def fake_ip(self, original):
        def build(rng):
            return f"10.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}"
        return self._cache(original, "IP_ADDRESS", build)

    def fake_ssn(self, original):
        def build(rng):
            return f"{rng.randint(100, 899):03d}-{rng.randint(10, 99):02d}-{rng.randint(1000, 9999):04d}"
        return self._cache(original, "SSN", build)

    def fake_credit_card(self, original):
        def build(rng):
            base = f"4{rng.randint(0, 999999999999999):015d}"
            return " ".join(base[i:i + 4] for i in range(0, 16, 4))
        return self._cache(original, "CREDIT_CARD", build)

    def fake_dob(self, original):
        def build(rng):
            return f"{rng.randint(1, 12):02d}/{rng.randint(1, 28):02d}/{rng.randint(1960, 2000)}"
        return self._cache(original, "DATE_OF_BIRTH", build)

    def fake_address(self, original):
        def build(rng):
            num = rng.randint(1, 999)
            street = rng.choice(STREETS)
            city, state, pin = rng.choice(CITIES)
            return f"{num} {street}, {city}, {state} {pin}"
        return self._cache(original, "ADDRESS", build)

    def fake_company(self, original):
        def build(rng):
            return f"{rng.choice(COMPANY_WORDS)} {rng.choice(COMPANY_SUFFIXES)}"
        return self._cache(original, "COMPANY_NAME", build)

    def fake_company_id(self, original):
        def build(rng):
            return f"U{rng.randint(10000, 99999)}XX{rng.randint(1900, 2020)}PLC{rng.randint(100000, 999999)}"
        return self._cache(original, "COMPANY_ID", build)

    def get(self, category, original):
        return {
            "PERSON_NAME": self.fake_name,
            "EMAIL": self.fake_email,
            "PHONE": self.fake_phone,
            "IP_ADDRESS": self.fake_ip,
            "SSN": self.fake_ssn,
            "CREDIT_CARD": self.fake_credit_card,
            "DATE_OF_BIRTH": self.fake_dob,
            "ADDRESS": self.fake_address,
            "COMPANY_NAME": self.fake_company,
            "COMPANY_ID": self.fake_company_id,
        }[category](original)

    def mapping_table(self):
        """Return {(category, original_key): fake} for reporting/audit."""
        return dict(self._map)
