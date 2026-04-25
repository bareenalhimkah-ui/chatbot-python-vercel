import json
import os


def load_client_config(client_id):
    """
    Lädt Kundendaten aus data/clients/
    """

    base_path = os.path.dirname(os.path.dirname(__file__))

    file_path = os.path.join(
        base_path,
        "data",
        "clients",
        f"{client_id}.json"
    )

    if not os.path.exists(file_path):
        raise ValueError(f"Kunde {client_id} nicht gefunden")

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_system_prompt(client_data):
    """
    Baut dynamischen Prompt pro Kunde
    """

    prompt = f"""
    Du bist die KI-Assistentin von {client_data['business_name']}.

    Branche:
    {client_data['industry']}

    Tonalität:
    {client_data['tone']}

    Kontaktdaten:
    {client_data['contact']}

    Standorte:
    {client_data['locations']}

    Leistungen:
    {client_data['services']}

    FAQ:
    {client_data['faq']}

    Nutze ausschließlich diese Informationen.
    Erfinde nichts.
    Bleibe freundlich und professionell.
    """

    return prompt