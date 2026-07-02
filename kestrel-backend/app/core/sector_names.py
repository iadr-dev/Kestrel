"""Sector name translations — maps FinMind sector IDs to localized display names."""

SECTOR_NAMES: dict[str, dict[str, str]] = {
    "Cement": {"zh-TW": "水泥", "en": "Cement"},
    "Food": {"zh-TW": "食品", "en": "Food"},
    "Plastics": {"zh-TW": "塑膠", "en": "Plastics"},
    "Textiles": {"zh-TW": "紡織", "en": "Textiles"},
    "ElectricMachinery": {"zh-TW": "電機", "en": "Electric Machinery"},
    "ElectricalCable": {"zh-TW": "電器電纜", "en": "Electrical Cable"},
    "GlassCeramic": {"zh-TW": "玻璃陶瓷", "en": "Glass/Ceramic"},
    "PaperPulp": {"zh-TW": "造紙", "en": "Paper/Pulp"},
    "IronSteel": {"zh-TW": "鋼鐵", "en": "Steel"},
    "Rubber": {"zh-TW": "橡膠", "en": "Rubber"},
    "Automobile": {"zh-TW": "汽車", "en": "Automobile"},
    "Electronic": {"zh-TW": "電子", "en": "Electronics"},
    "BuildingMaterialConstruction": {"zh-TW": "營建", "en": "Construction"},
    "ShippingTransportation": {"zh-TW": "航運", "en": "Shipping"},
    "Tourism": {"zh-TW": "觀光", "en": "Tourism"},
    "FinancialInsurance": {"zh-TW": "金融保險", "en": "Financial"},
    "TradingConsumersGoods": {"zh-TW": "貿易百貨", "en": "Trading"},
    "OilGasElectricity": {"zh-TW": "油電燃氣", "en": "Oil/Gas/Power"},
    "Semiconductor": {"zh-TW": "半導體", "en": "Semiconductor"},
    "ComputerPeripheralEquipment": {"zh-TW": "電腦周邊", "en": "Computer Peripherals"},
    "Optoelectronic": {"zh-TW": "光電", "en": "Optoelectronic"},
    "CommunicationsInternet": {"zh-TW": "通信網路", "en": "Communications"},
    "ElectronicPartsComponents": {"zh-TW": "電子零組件", "en": "Electronic Parts"},
    "ElectronicProductsDistribution": {"zh-TW": "電子通路", "en": "E-Commerce"},
    "InformationService": {"zh-TW": "資訊服務", "en": "IT Services"},
    "OtherElectronic": {"zh-TW": "其他電子", "en": "Other Electronics"},
    "OtherElectronicIndustries": {"zh-TW": "其他電子", "en": "Other Electronics"},
    "BiotechnologyMedicalCare": {"zh-TW": "生技醫療", "en": "Biotech/Medical"},
    "Chemical": {"zh-TW": "化學", "en": "Chemical"},
    "ChemicalBiotechnologyMedicalCare": {"zh-TW": "化學生技醫療", "en": "Chemical/Biotech"},
    "CulturalCreative": {"zh-TW": "文化創意", "en": "Cultural Creative"},
    "GreenEnergyEnvironmentServices": {"zh-TW": "綠能環保", "en": "Green Energy"},
    "GreenEnergyEnvironmentalServices": {"zh-TW": "綠能環保", "en": "Green Energy"},
    "DigitalCloudServices": {"zh-TW": "數位雲端", "en": "Digital Cloud"},
    "SportsLeisure": {"zh-TW": "運動休閒", "en": "Sports/Leisure"},
    "Household": {"zh-TW": "居家生活", "en": "Home/Living"},
    "Other": {"zh-TW": "其他", "en": "Other"},
    "TAIEX": {"zh-TW": "加權指數", "en": "TAIEX"},
    "TPExIndex": {"zh-TW": "櫃買指數", "en": "TPEx"},
    "NonElectronicsSubIndex": {"zh-TW": "非電子類", "en": "Non-Electronics"},
    "NonFinanceSubIndex": {"zh-TW": "非金融類", "en": "Non-Financial"},
    "NonFinanceNonElectronicsSubIndex": {"zh-TW": "非金融非電子", "en": "Non-Fin/Non-Elec"},
}


def get_sector_name(sector_id: str, locale: str = "zh-TW") -> str:
    """Get localized display name for a sector ID."""
    names = SECTOR_NAMES.get(sector_id)
    if not names:
        return sector_id
    return names.get(locale, names.get("zh-TW", sector_id))
