ALL = "전체"


OFFICES = {
    ALL: [ALL],
    "서울": ["서울특별시교육청"],
    "부산": ["부산광역시교육청"],
    "대구": ["대구광역시교육청"],
    "인천": ["인천광역시교육청"],
    "광주": ["광주광역시교육청"],
    "대전": ["대전광역시교육청"],
    "울산": ["울산광역시교육청"],
    "세종": ["세종특별자치시교육청"],
    "경기": ["경기도교육청"],
    "강원": ["강원특별자치도교육청"],
    "충북": ["충청북도교육청"],
    "충남": ["충청남도교육청"],
    "전북": ["전북특별자치도교육청"],
    "전남": ["전라남도교육청"],
    "경북": ["경상북도교육청"],
    "경남": ["경상남도교육청"],
    "제주": ["제주특별자치도교육청"],
}


# The first value is the canonical storage value. Remaining values preserve
# compatibility with existing NEIS records that use an alternate regional name.
REGION_VALUES = {
    "서울": ("서울특별시",),
    "부산": ("부산광역시",),
    "대구": ("대구광역시",),
    "인천": ("인천광역시",),
    "광주": ("광주광역시", "전남광주통합특별시(광주)"),
    "대전": ("대전광역시",),
    "울산": ("울산광역시",),
    "세종": ("세종특별자치시",),
    "경기": ("경기도",),
    "강원": ("강원특별자치도",),
    "충북": ("충청북도",),
    "충남": ("충청남도",),
    "전북": ("전북특별자치도",),
    "전남": ("전라남도", "전남광주통합특별시(전남)"),
    "경북": ("경상북도",),
    "경남": ("경상남도",),
    "제주": ("제주특별자치도",),
}


OFFICE_VALUES = {
    "서울특별시교육청": ("서울특별시교육청", "서울시교육청"),
    "부산광역시교육청": ("부산광역시교육청", "부산시교육청"),
    "대구광역시교육청": ("대구광역시교육청", "대구시교육청"),
    "인천광역시교육청": ("인천광역시교육청", "인천시교육청"),
    "광주광역시교육청": ("광주광역시교육청", "광주시교육청"),
    "대전광역시교육청": ("대전광역시교육청", "대전시교육청"),
    "울산광역시교육청": ("울산광역시교육청", "울산시교육청"),
    "세종특별자치시교육청": ("세종특별자치시교육청", "세종시교육청"),
    "경기도교육청": ("경기도교육청",),
    "강원특별자치도교육청": ("강원특별자치도교육청", "강원도교육청"),
    "충청북도교육청": ("충청북도교육청", "충북도교육청"),
    "충청남도교육청": ("충청남도교육청", "충남도교육청"),
    "전북특별자치도교육청": ("전북특별자치도교육청", "전라북도교육청"),
    "전라남도교육청": ("전라남도교육청", "전남도교육청"),
    "경상북도교육청": ("경상북도교육청", "경북도교육청"),
    "경상남도교육청": ("경상남도교육청", "경남도교육청"),
    "제주특별자치도교육청": ("제주특별자치도교육청", "제주도교육청"),
}


def _clean(value):
    return str(value or "").strip()


def normalize_region(value):
    """Return the canonical database region value for an input value."""
    region = _clean(value)
    if not region or region == ALL:
        return region

    for values in REGION_VALUES.values():
        if region in values:
            return values[0]
    return region


def normalize_office(value):
    """Return a whitespace-normalized education-office value."""
    office = _clean(value)
    for values in OFFICE_VALUES.values():
        if office in values:
            return values[0]
    return office


def region_filter_values(region):
    """Return all stored values compatible with a selected UI region."""
    selected_region = _clean(region)
    if selected_region == ALL:
        return ()
    return REGION_VALUES.get(selected_region, (normalize_region(selected_region),))


def office_filter_values(office):
    """Return all stored values compatible with a selected education office."""
    selected_office = _clean(office)
    if selected_office == ALL:
        return ()
    return OFFICE_VALUES.get(selected_office, (normalize_office(selected_office),))
