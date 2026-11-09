# generate_dataset.py
import json
import os
import random
import re

import openpyxl

# Dataset will be pulled from under 'Data' directory.
# File setup
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, "data")
os.makedirs(data_dir, exist_ok=True)


def find_local_sample_file():
    """Find the first available workbook to use as the source for this run."""
    # Check the shared workbook location first, then the copy inside this project.
    candidates = [
        '/Users/cristina/Partners HealthCare Dropbox/Christian Bekalu/Zoe_Garance_Stimbank/website/Sample_Christian_2.xlsx',
        os.path.join(data_dir, 'Sample_Christian_2.xlsx'),
    ]
    # Ignore missing and empty files so generation never reads an unusable workbook.
    for candidate in candidates:
        if candidate and os.path.exists(candidate) and os.path.getsize(candidate) > 0:
            return candidate
    return None


def row_value(row, idx, column_name, default=None):
    """Read a cell by its header name, or return a default if the column is absent."""
    # idx maps each column title to its position in the row tuple.
    column_index = idx.get(column_name)
    if column_index is None or column_index >= len(row):
        return default
    return row[column_index]


def extract_doi(article):
    """Find a DOI inside the Article citation and remove trailing punctuation."""
    # Article cells contain a full citation, so the DOI is embedded in other text.
    match = re.search(r'10\.\d{4,9}/\S+', str(article or ''), re.IGNORECASE)
    return match.group(0).rstrip(').,;]') if match else ''

# Read x/y/z MNI coordinates from the Excel row if present.
def parse_mni_xyz(row, idx):
    x_key = "EBS coordinates (MNI space) x"
    y_key = "EBS coordinates (MNI space) y"
    z_key = "EBS coordinates (MNI space) z"

    x = row[idx.get(x_key, -1)] if x_key in idx else None
    y = row[idx.get(y_key, -1)] if y_key in idx else None
    z = row[idx.get(z_key, -1)] if z_key in idx else None

    try:
        if x is None or y is None or z is None:
            return None
        return [float(x), float(y), float(z)]
    except (TypeError, ValueError):
        return None

# Load publication metadata from stimbank dataset
def load_local_sample_publications(excel_path):
    """Create one publication record for each distinct Publication label."""
    if not excel_path or not os.path.exists(excel_path):
        return []

    # Read cached cell values from the first worksheet without modifying the file.
    try:
        wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
    except Exception:
        return []

    if not wb.sheetnames:
        return []

    ws = wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []

    header = [str(cell).strip() if cell is not None else "" for cell in rows[0]]
    # Use names rather than hard-coded positions for publication details.
    idx = {name: i for i, name in enumerate(header)}

    publications = []
    # The workbook repeats citations on every site row; this set prevents duplicates.
    seen = set()

    for row in rows[1:]:
        # Skip completely blank rows before reading any fields.
        if not row or not any(cell is not None and str(cell).strip() for cell in row):
            continue

        # Reads the first column from the dataset as the publication label.
        label = str(row_value(row, idx, 'Publication', row[0]) or '').strip()
        if not label:
            continue

        # Only add each label once, even when it appears on many site rows.
        if label in seen:
            continue
        seen.add(label)

        # Article holds the longer citation, including the DOI when one is present.
        article = str(row_value(row, idx, 'Article', '') or '').strip()

        # Define columns containing study details: pathology, procedure, and sample size.
        pathology = str(row_value(row, idx, 'Pathology', 'Not specified') or 'Not specified').strip() or 'Not specified'
        procedure = str(row_value(row, idx, 'EBS procedure', 'Not specified') or 'Not specified').strip() or 'Not specified'
        sample_size = row_value(row, idx, 'Sample size', 0)

        # Some spreadsheets store numbers with commas, so remove them before conversion.
        try:
            sample_size_value = int(float(str(sample_size).replace(',', '')))
        except Exception:
            sample_size_value = 0

        # Prefer the year in the short label; use the full citation if needed.
        year_match = re.search(r'\b(?:19|20)\d{2}\b', label) or re.search(r'\b(?:19|20)\d{2}\b', article)
        year = int(year_match.group(0)) if year_match else 0

        # Keep a structured publication record for the website's search and details view.
        publications.append({
            'id': f'LOCAL{len(publications) + 1:03d}',
            'authors': label[:120],
            'year': year,
            'title': article or label,
            'journal': 'Local sample dataset',
            'country': str(row_value(row, idx, 'Region', 'Local dataset') or 'Local dataset').strip() or 'Local dataset',
            'institution': 'Local sample dataset',
            'sample_size': sample_size_value,
            'patient_population': pathology,
            'procedure_type': procedure,
            'doi': extract_doi(article),
            'pmid': ''
        })

    return publications


def safe_float(value):
    """Parse a numeric value from the Excel workbook and return None if invalid."""
    if value is None:
        return None
    # Coordinates may arrive as numbers or as strings containing commas/spaces.
    try:
        return float(str(value).replace(',', '').strip())
    except (TypeError, ValueError):
        return None



# # Defining how data is mapped from a dataset (assuming it follows the StimBank excel template)


# Each tuple is (website domain, workbook's main-domain header, start column, end column).
# Python counts columns from zero and excludes the end, so H:AD is written as 7:30.
# The column ranges for each domain are H:AD, AE:AN, AO:AU, AV:BF, BG:BT, BU, BV, BW, and BX.
SAMPLE_CATEGORY_COLUMNS = (
    ('Sensory', 'Sensory-Perceptual', 7, 30),
    ('Affective', 'Affective', 30, 40),
    ('Autonomic', 'Autonomic', 40, 47),
    ('Cognitive', 'Cognitive/language', 47, 58),
    ('Motor', 'Motor', 58, 72),
    ('Consciousness', 'Altered consciousness/awareness', 72, 73),
    ('Agency', 'Agency', 73, 74),
    ('No Effect', 'No effect', 74, 75),
    ('Other/ unclassifiable responses', 'Other/unclassifiable', 75, 76),
)

# Sample dataset does not use the same wording as the website taxonomy. Below are the proposed aliases.
SAMPLE_SUBDOMAIN_ALIASES = {
    ('Affective', 'positive'): 'Positive valence responses',
    ('Affective', 'negative'): 'Negative valence responses',
    ('Autonomic', 'visceralincludingepigastricsensations'): 'Visceral responses',
    ('Cognitive', 'language'): 'Language disturbances',
    ('Motor', 'negativearrestslowingdisturbances'): 'Negative',
}

# These entries do the same for response-type headers; suffix numbers distinguish
# repeated Excel columns and are removed before matching below.
SAMPLE_RESPONSE_TYPE_ALIASES = {
    ('Sensory', 'Auditory', 'simpleperception'): 'Auditory Simple',
    ('Sensory', 'Auditory', 'complexperception'): 'Auditory Complex',
    ('Sensory', 'Auditory', 'illusion'): 'Auditory Illusions',
    ('Sensory', 'Visual', 'simpleperception'): 'Visual Simple',
    ('Sensory', 'Visual', 'complexperception'): 'Visual Complex',
    ('Sensory', 'Visual', 'illusion'): 'Visual Illusions',
    ('Cognitive', 'Language disturbances', 'speech'): 'Production',
    ('Cognitive', 'Language disturbances', 'lexicalphonologicalgrammarerrors'): 'Production',
}


def is_true_flag(value):
    """Return True only for an Excel boolean TRUE or the text 'true'."""
    return value is True or (isinstance(value, str) and value.strip().casefold() == 'true')


def is_one_flag(value):
    """Return True for numeric 1 cells, but not boolean TRUE cells."""
    # Excel booleans are also numeric-like in Python, so handle them separately.
    if value is None or isinstance(value, bool):
        return False
    # Convert strings like '1' and numbers like 1.0 to the same comparison value.
    try:
        return float(str(value).strip()) == 1
    except (TypeError, ValueError):
        return False


def clean_category_label(label):
    """Remove a trailing number Excel uses to distinguish duplicate headers."""
    return re.sub(r'\d+$', '', str(label or '').strip()).strip()


def normalize_taxonomy_label(label):
    """Make two labels comparable by ignoring case, spaces, and punctuation."""
    return re.sub(r'[^a-z0-9]', '', clean_category_label(label).casefold())


def find_taxonomy_subdomain(category, label):
    """Find the taxonomy subdomain matching a workbook header, if it exists."""
    # Apply an explicit alias first for headers whose wording differs substantially.
    normalized_label = normalize_taxonomy_label(label)
    alias = SAMPLE_SUBDOMAIN_ALIASES.get((category, normalized_label))
    if alias:
        normalized_label = normalize_taxonomy_label(alias)

    # Otherwise compare normalized names against the selected domain's subdomains.
    for subdomain in taxonomy_schema.get(category, {}).get('subdomains', []):
        normalized_name = normalize_taxonomy_label(subdomain.get('name', ''))
        # Some workbook labels omit a trailing word such as "responses".
        if normalized_label == normalized_name or normalized_label == normalized_name.removesuffix('responses'):
            return subdomain
    return None


def find_taxonomy_response_type(category, subdomain_name, label):
    """Return the canonical response-type name that matches a workbook header."""
    # Normalize and alias the workbook label before looking through schema names.
    normalized_label = normalize_taxonomy_label(label)
    alias = SAMPLE_RESPONSE_TYPE_ALIASES.get((category, subdomain_name, normalized_label))
    if alias:
        normalized_label = normalize_taxonomy_label(alias)

    # Response types normally belong to a subdomain; some domains define them directly.
    category_schema = taxonomy_schema.get(category, {})
    subdomain = next((
        item for item in category_schema.get('subdomains', [])
        if item.get('name') == subdomain_name
    ), None)
    # Convert either supported schema format (list or dictionary) to a list of names.
    response_types, _ = normalize_response_types(
        subdomain.get('response_types', []) if subdomain else category_schema.get('response_types', [])
    )
    # Return the spelling used by the taxonomy, not the workbook's variant.
    return next((
        response_type for response_type in response_types
        if normalize_taxonomy_label(response_type) == normalized_label
    ), None)


def load_local_sample_sites(excel_path):
    """Turn each valid workbook row into one website stimulation-site record."""
    if not excel_path or not os.path.exists(excel_path):
        return []

    # Open the workbook read-only and use displayed values rather than formulas.
    try:
        wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
    except Exception:
        return []

    if not wb.sheetnames:
        return []

    ws = wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []

    header = [str(cell).strip() if cell is not None else "" for cell in rows[0]]
    # Build a header-to-position lookup so the fields below stay readable.
    idx = {name: i for i, name in enumerate(header)}
    # Columns that are to be present in the database; without them a site cannot be identified or mapped.
    required = [
        'Publication',
        'Article',
        'Patient ID',
        'Pathology',
        'EBS procedure',
        'Side of stimulation',
        'EBS coordinates (MNI space) x',
        'EBS coordinates (MNI space) y',
        'EBS coordinates (MNI space) z',
    ]
    if not all(key in idx for key in required):
        return []

    sites = []

    for row_index, row in enumerate(rows[1:], start=2):
        # Ignore empty rows, then accept only rows with a recognized left/right side.
        if not row or not any(cell is not None and str(cell).strip() for cell in row):
            continue

        side = str(row_value(row, idx, 'Side of stimulation', '') or '').strip().casefold()
        if side not in {'left', 'right'}:
            continue

        # Read all three MNI coordinates; a row without a complete coordinate is skipped.
        x = safe_float(row_value(row, idx, 'EBS coordinates (MNI space) x'))
        y = safe_float(row_value(row, idx, 'EBS coordinates (MNI space) y'))
        z = safe_float(row_value(row, idx, 'EBS coordinates (MNI space) z'))
        if x is None or y is None or z is None:
            continue

        # Find the first selected main domain in the documented column order.
        # TRUE is used for domain flags; a single-column domain without subdomains may instead use 1.
        selected_group = None
        for category, expected_header, start, end in SAMPLE_CATEGORY_COLUMNS:
            if start >= len(row) or header[start].casefold() != expected_header.casefold():
                continue
            if is_true_flag(row[start]) or is_one_flag(row[start]):
                selected_group = (category, start, end)
                break

        if selected_group is None:
            # Rows with no recognized domain cannot be included in the category filters.
            continue

        # Keep the domain's name and the range of columns that belong to it.
        category, start, end = selected_group
        subdomain_schema = None
        subdomain_column = None
        # Within that domain, find the first active header that exists in the taxonomy.
        for column in range(start + 1, min(end, len(row))):
            if not (is_true_flag(row[column]) or is_one_flag(row[column])):
                continue
            subdomain_schema = find_taxonomy_subdomain(category, header[column])
            if subdomain_schema:
                subdomain_column = column
                break

        # Use the taxonomy's canonical spelling; if none exists, mark the site domain-only.
        subdomain_name = subdomain_schema['name'] if subdomain_schema else category

        response_types = []
        if subdomain_schema:
            # Match the remaining active cells to this subdomain's allowed response types.
            for column in range(start + 1, min(end, len(row))):
                if column == subdomain_column or not (is_true_flag(row[column]) or is_one_flag(row[column])):
                    continue
                response_type = find_taxonomy_response_type(category, subdomain_name, header[column])
                if response_type and response_type not in response_types:
                    response_types.append(response_type)
        else:
            # Domains without subdomains can define response types at the domain level.
            response_types, _ = normalize_response_types(
                taxonomy_schema.get(category, {}).get('response_types', [])
            )

        # Read publication, patient, clinical, and effect details by their column titles.
        publication = str(row_value(row, idx, 'Publication', '') or '').strip() or 'Unknown publication'
        article = str(row_value(row, idx, 'Article', '') or '').strip()
        region = str(row_value(row, idx, 'Site of EBS evoking a response', '') or row_value(row, idx, 'Brain area explored', '') or 'Unknown region').strip() or 'Unknown region'
        effect = str(row_value(row, idx, 'Phenomenological description', '') or region).strip() or 'Stimulated site'
        pathology = str(row_value(row, idx, 'Pathology', 'Unknown pathology') or 'Unknown pathology').strip() or 'Unknown pathology'
        procedure = str(row_value(row, idx, 'EBS procedure', 'Unknown procedure') or 'Unknown procedure').strip() or 'Unknown procedure'
        patient_id = str(row_value(row, idx, 'Patient ID', f'ROW{row_index}') or f'ROW{row_index}').strip()
        age = safe_float(row_value(row, idx, 'Age (years)'))
        sex = str(row_value(row, idx, 'Sex', 'Unknown') or 'Unknown').strip() or 'Unknown'
        publication_year = re.search(r'\b(?:19|20)\d{2}\b', publication) or re.search(r'\b(?:19|20)\d{2}\b', article)
        country = str(row_value(row, idx, 'Region', '') or '').strip()

        # Store the fields used by the database table, viewer, and detail modal.
        sites.append({
            'id': f'WORKBOOK{len(sites) + 1:03d}',
            'patient_id': patient_id,
            'patient_display': patient_id,
            'category': category,
            'subcategory': subdomain_name or category,
            'domain': category,
            'subdomain': subdomain_name or category,
            'response_types': response_types,
            'effect': effect,
            'description': effect,
            'raw_description': effect,
            'region': region,
            'hemisphere': 'L' if side == 'left' else 'R',
            'mni': [x, y, z],
            'procedure': procedure,
            'pathology': pathology,
            'frequency_hz': safe_float(row_value(row, idx, 'Stimulation parameters Frequency (Hz)')),
            'current_ma': safe_float(row_value(row, idx, 'Stimulation parameters Intensity')),
            'pulse_width_ms': safe_float(row_value(row, idx, 'Stimulation parameters  Pulse width (ms)')),
            'bipolar': True,
            'pub_id': publication,
            # Keep the short label and full citation separately; extract DOI for its link.
            'publication': {
                'label': publication,
                'title': publication,
                'article': article,
                'authors': publication,
                'year': int(publication_year.group(0)) if publication_year else 0,
                'journal': '',
                'country': country,
                'doi': extract_doi(article),
            },
            'patient_age': int(age) if age is not None else 0,
            'patient_sex': sex,
        })

    return sites

publications = []

local_sample_path = find_local_sample_file()
if local_sample_path:
    publications = load_local_sample_publications(local_sample_path)
    print(f"Loaded publication metadata from local sample dataset: {local_sample_path}")
else:
    print("No local sample dataset found. Dataset generation is disabled until a workbook is available.")

# Modified by Christian
# Contains updated definitions of domains and sub-domains from Methods.docx
#
# Preferred source format for subdomains:
#   "response_types": {
#       "Auditory Simple": "Simple percepts such as ringing or buzzing.",
#       "Auditory Complex": "More complex sounds such as voices or music.",
#       "Auditory Illusions": "Illusory auditory phenomena such as pitch shifts."
#   },
#   "sites": [
#       "Heschl's Gyrus (A1)",
#       "Superior Temporal Gyrus",
#       "Planum Temporale"
#   ]
#
# This keeps the response type definitions in a dedicated second block, while "sites"
# remains a separate list 

def clean_site_name(site_name):
    """Remove coordinate values from site labels while preserving the anatomical name."""
    if site_name is None:
        return ""

    cleaned = str(site_name).strip()
    cleaned = re.sub(r"\s*\(\s*-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?\s*\)", "", cleaned)
    cleaned = re.sub(r"\s*\[\s*-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?\s*\]", "", cleaned)
    cleaned = re.sub(r"\s*[,;]\s*$", "", cleaned)
    return cleaned.strip()


def normalize_response_types(response_types):
    """Accept either a list of names or a {name: definition} dict and return ordered names plus definitions."""
    if isinstance(response_types, dict):
        ordered_types = []
        definitions = {}
        for response_name, definition in response_types.items():
            name = str(response_name).strip()
            if not name:
                continue
            ordered_types.append(name)
            if isinstance(definition, str):
                cleaned_definition = definition.strip()
            else:
                cleaned_definition = str(definition).strip()
            if cleaned_definition:
                definitions[name] = cleaned_definition
        return ordered_types, definitions

    if isinstance(response_types, list):
        ordered_types = []
        definitions = {}
        for item in response_types:
            if isinstance(item, dict):
                name = str(item.get('name', '')).strip()
                definition = item.get('definition', '')
            else:
                name = str(item).strip()
                definition = ""

            if not name:
                continue
            ordered_types.append(name)
            if isinstance(definition, str):
                cleaned_definition = definition.strip()
            else:
                cleaned_definition = str(definition).strip()
            if cleaned_definition:
                definitions[name] = cleaned_definition
        return ordered_types, definitions

    return [], {}

# Classification of functional responses: used for front page and Methods page, as well as for the filters in the Database and 3D Viewer pages
taxonomy_schema = {
    "Sensory": {
        "color": "#93C5FD",
        "description": "Sensory or perceptual responses, classified by sensory modality",
        "regions": ["Postcentral Gyrus (S1)", "Parietal Operculum (S2)", "Calcarine Sulcus (V1)", "Fusiform Face Area (FFA)", "Heschl's Gyrus (A1)", "Posterior Insula", "Temporoparietal Junction (TPJ)"],
        "subdomains": [
            {
                "name": "Auditory",
                "definition": "Evoked simple perceptions (ringing, water running, mumbling, buzzing, whistle), complex perceptions (voices, music), or auditory illusions (pitch change, sounds louder, ear obstruction, sound distortion).",
                "hubs": ["Heschl's Gyrus (A1)", "Superior Temporal Gyrus", "Planum Temporale"],
                "response_types": [
                    "Auditory Simple",
                    "Auditory Complex",
                    "Auditory Illusions",
                ],
                "sites": ["Heschl's Gyrus (A1)", "Superior Temporal Gyrus", "Planum Temporale"]
            },
            {
                "name": "Visual",
                "definition": "Evoked simple perceptions (phosphenes, flashes, shadows, shapes, moving dots), complex perceptions (faces, characters, scenes, cartoons), or visual illusions (halo, metamorphopsia, micropsia/macropsia, visual motion).",
                "hubs": ["Calcarine Sulcus (V1)", "Lingual Gyrus (V2)", "Fusiform Face Area (FFA)", "Middle Temporal (MT/V5)"],
                "response_types": [
                    "Visual Simple",
                    "Visual Complex",
                    "Visual Illusions"
                ],
                "sites": ["Calcarine Sulcus (V1)", "Fusiform Face Area (FFA)", "Middle Temporal Visual Area (MT/V5)"]
            },
            {
                "name": "Gustatory",
                "definition": "Identifiable or non-identifiable gustatory (taste), further classified by pleasant or unpleasant hedonic valence.",
                "hubs": ["Anterior Insular Operculum", "Piriform Cortex / Uncus", "Mesial Temporal Operculum"],
                "response_types": [
                    "Pleasant",
                    "Unpleasant"
                ],
                "sites": ["Anterior Insular Operculum", "Anterior Insular Operculum"]
            },
            {
                "name": "Olfactory",
                "definition": "Evoked olfactory (smell) perceptions, which can be identifiable or non-identifiable, and may have pleasant or unpleasant hedonic valence.",
                "hubs": ["Piriform Cortex / Uncus", "Anterior Insular Operculum", "Orbitofrontal Cortex"],
                "response_types": [
                    "Pleasant",
                    "Unpleasant"
                ],
                "sites": ["Piriform Cortex / Uncus", "Piriform Cortex / Uncus"]
            },
            {
                "name": "Vestibular",
                "definition": "Simple sensations of dizziness or vertigo, as well as complex whole-body displacement, graviceptive experiences (falling, floating, levitation), or rotation.",
                "hubs": ["Parieto-Insular Vestibular Cortex (PIVC)", "Posterior Insular Operculum", "Superior Temporal Sulcus"],
                "response_types": [],
                "sites": ["Parieto-Insular Vestibular Cortex (PIVC)"]
            },
            {
                "name": "Body Perception",
                "definition": "Disturbances of body schema or image, such as out-of-body experiences, alien limb sensations, limb loss sensations, limb appearing to move, autoscopic and heautoscopic phenomena.",
                "hubs": ["Right Temporoparietal Junction (TPJ)", "Right Angular Gyrus", "Inferior Parietal Lobule"],
                "response_types": [],
                "sites": ["Right Temporoparietal Junction (TPJ)"]
            },
            {
                "name": "Somatosensory",
                "definition": "Somatosensory responses mapped by body part (upper limb, lower limb, head/neck/trunk) and classified as painful (burning, pinprick, muscle pain) or non-painful (tingling, thermal warmth, numbness, vibration, pressure).",
                "hubs": ["Postcentral Gyrus (S1)", "Parietal Operculum (S2)", "Paracentral Lobule", "Dorsal Posterior Insula"],
                "response_types": [
                    "Non-Painful",
                    "Painful",
                    "Upper Limb",
                    "Lower Limb",
                    "Head/Neck/Trunk",
                ],
                "sites": ["Postcentral Gyrus (S1)", "Dorsal Posterior Insula", "Postcentral Gyrus (S1)", "Paracentral Lobule", "Dorsal Posterior Insula"]
            }
        ]
    },
    "Motor": {
        "color": "#8E7CC3",
        "description": "Motor responses, positive or negative, classified by effector.",
        "regions": ["Precentral Gyrus (Hand Knob)", "Supplementary Motor Area (SMA)", "Frontal Eye Field (FEF)", "Subthalamic Nucleus (STN)", "VIM Thalamus"],
        "subdomains": [
            {
                "name": "Positive",
                "definition": "Positive motor responses were defined as any evoked movement (indicated by terms such as movement, contraction, myoclonic, tonic, clonic, lifting, flexion, pronation, twitching, jerk, tremor, shaking). Further classified by effector, including upper limb (shoulder, arm, hand, fingers), lower limb (hip, leg, foot), head/neck/trunk, articulatory (tongue, lips, jaw, larynx), and/or eyes.",
                "hubs": ["Precentral Gyrus (M1 Hand Knob)", "Paracentral Lobule", "SMA"],
                "response_types": [
                    "Upper limb",
                    "Lower limb",
                    "Head/neck/trunk",
                    "Articulatory",
                    "Eyes",
                ],
                "sites": ["Precentral Gyrus (Hand Knob)", "Precentral Gyrus (M1)", "Supplementary Motor Area (SMA)", "Precentral Gyrus (M1)", "Frontal Eye Field (FEF)"]
            },
            {
                "name": "Negative",
                "definition": "Negative responses were defined as arrest, disturbance, or slowing of movements. Further classified including upper limb (shoulder, arm, hand, fingers), lower limb (hip, leg, foot), head/neck/trunk, articulatory (tongue, lips, jaw, larynx), and/or eyes.",
                "hubs": ["Frontal Eye Field (FEF)", "Superior Frontal Sulcus"],
                "response_types": [
                    "Upper limb",
                    "Lower limb",
                    "Head/neck/trunk",
                    "Articulatory",
                    "Eyes",
                ],
                "sites": ["Frontal Eye Field (FEF)", "Superior Frontal Sulcus", "Superior Frontal Sulcus", "Superior Frontal Sulcus (FEF)", "Superior Frontal Sulcus"]
            },
            {
                "name": "Automatisms",
                "definition": "Automatisms such as laughter without merriment or mirth, grasping, rubbing, vocalizations (excluding simple motor phenomena), yawning, chewing/mastication, oro-alimentary automatisms.",
                "hubs": ["Frontal Eye Field (FEF)", "Superior Frontal Sulcus"],
                "response_types": [],
                "sites": ["Frontal Eye Field (FEF)"]
            }
        ]
    },
    "Cognitive": {
        "color": "#E598D8",
        "description": "Disturbances of cognitive processes, including language, memory- and familiarity-related processes, and other focal cognitive processes.",
        "regions": ["Middle Frontal Gyrus", "Pars Opercularis (Broca)", "Posterior STG (Wernicke)", "Entorhinal Cortex", "Hippocampus", "DLPFC", "Temporoparietal Junction (TPJ)"],
        "subdomains": [
            {
                "name": "Language disturbances",
                "definition": "Disruptions in language production (such as complete interruption of speech or errors), comprehension (Impairment in understanding the meaning of verbal information) or written language (reading and writing impairment).",
                "hubs": ["Pars Opercularis (Broca's Area)", "Ventral Premotor Cortex", "SMA"],
                "response_types": [
                    "Production",
                    "Comprehension",
                    "Written Language",
                ],
                "sites": ["Pars Opercularis (Broca's Area)", "Ventral Premotor Cortex (vPMC)", "Ventral Premotor Cortex (vPMC)"]
            },
            {
                "name": "Derealization / Depersonalization",
                "definition": "Feelings of derealization or depersonalization, such as feeling detached from the world or inside a dream, or feeling of going into a trance.",
                "hubs": ["Posterior STG (Wernicke)", "Pars Triangularis", "VWFA", "pMTG"],
                "response_types": [],
                "sites": ["Pars Triangularis (IFG)"]
            },
            {
                "name": "Reminiscence/Déjà rêvé",
                "definition": "Evoked visual, auditory, or multimodal complex perceptions accompanied by a subjective feeling of remembering or reexperiencing (e.g., flashbacks, recollection of a dream).",
                "hubs": ["Hippocampus (CA1 / Subiculum)", "Entorhinal Cortex", "Lateral Temporal Sulcus"],
                "response_types": [],
                "sites": ["Hippocampus (CA1 / Subiculum)"]
            },
            {
                "name": "Déjà vu/Déjà vécu/Jamais vu",
                "definition": "Erroneous feelings of familiarity (déjà vu/déjà vécu) or unfamiliarity (jamais vu) for the current situation. Contrary to reminiscences and déjà rêvé, these phenomena are devoid of perceptual content.",
                "hubs": ["Temporoparietal Junction (TPJ)", "Dorsomedial Prefrontal Cortex (dmPFC)"],
                "response_types": [],
                "sites": ["Temporoparietal Junction (TPJ)"]
            },
            {
                "name": "Other Focal Cognitive Changes",
                "definition": "Focal cognitive changes, which included for example dyscalculia, working memory deficits, music processing disruptions, face recognition/discrimination deficits, or emotion recognition deficits.",
                "hubs": ["Dorsolateral Prefrontal Cortex (DLPFC)", "Anterior Cingulate"],
                "response_types": [],
                "sites": ["Dorsolateral Prefrontal Cortex (DLPFC)"]
            }
        ]
    },
    "Affective": {
        "color": "#FDB082",
        "description": "Evoked emotional experiences or changes in affect.",
        "regions": ["Basolateral Amygdala", "Anterior Cingulate (ACC)", "Anterior Midcingulate (aMCC)", "Subgenual Area 25", "Nucleus Accumbens"],
        "subdomains": [
            {
                "name": "Positive valence responses",
                "definition": "Positive changes in affect, such as happiness/wellbeing (described as contentment or pleasant mood), ecstatic/bliss (characterized by profound bliss, euphoria, or heightened wellbeing) or mirth (amusement or laughter-like affective responses)",
                "hubs": ["Basolateral Amygdala", "Anterior Insula"],
                "response_types": [
                    "Happiness/Wellbeing",
                    "Ecstatic/Bliss",
                    "Mirth"
                ],
                "sites": ["Basolateral Amygdala", "Anterior Insula (Affective Core)", "Anterior Insula (Affective Core)"]
            },
            {
                "name": "Negative valence responses",
                "definition": "Negative changes in affect such as anger (irritability or hostile emotional arousal), anxiety (anxious or apprehensive emotional states, often with worry or tension), fear (fearful affective states including panic, dread, or apprehension of threat), or sadness (including despair, or emotional dysphoria).",
                "hubs": ["Anterior Cingulate Cortex (ACC)", "Pre-SMA Affective Interface"],
                "response_types": [
                    "Anger",
                    "Anxiety",
                    "Fear",
                    "Sadness"
                ],
                "sites": ["Anterior Cingulate Cortex (ACC)", "Anterior Cingulate Cortex (ACC)", "Pre-SMA Affective Interface", "Pre-SMA Affective Interface"]
            }
        ]
    },
    "Autonomic": {
        "color": "#F6DE68",
        "description": "Central autonomic network regulating visceral interoception, cardiac rhythm, vasomotor tone, and neurovegetative reflexes.",
        "regions": ["Anterior Insular Cortex", "Periaqueductal Gray (PAG)", "Hypothalamus", "Medial Prefrontal Cortex"],
        "subdomains": [
            {
                "name": "Cardiovascular responses",
                "definition": "Change in heart rate (subjective or objectively measured) or changes in blood pressure.",
                "hubs": ["Anterior-Inferior Insula", "Mesial Temporal Operculum"],
                "response_types": [],
                "sites": ["Anterior-Inferior Insula"]
            },
            {
                "name": "Temperature responses",
                "definition": "General sensations of cold or warmth (e.g. being cold, being warm, heat wave sensation, flushing, sweating).",
                "hubs": ["Posterior Insular Cortex", "Subgenual Anterior Cingulate"],
                "response_types": [],
                "sites": ["Posterior Insular Cortex"]
            },
            {
                "name": "Visceral responses",
                "definition": "Sudden facial flushing, skin sensation of extreme heat or localized vasoconstriction and sudden chill.",
                "hubs": ["Hypothalamus", "Anterior Insular Operculum"],
                "response_types": [],
                "sites": ["Hypothalamus / Periventricular Core"]
            },
            {
                "name": "Pupillary responses",
                "definition": "Pupillary responses.",
                "hubs": ["Periaqueductal Gray (PAG)", "Anterior Midcingulate Cortex"],
                "response_types": [],
                "sites": ["Periaqueductal Gray (PAG)"]
            },
            {
                "name": "Respiratory responses",
                "definition": "Responses such as hypoventilation/apnea, hyperventilation/shortness of breath, or hypoxemia.",
                "hubs": ["Hypothalamic Nuclei", "Opercular Visceral Area"],
                "response_types": [],
                "sites": ["Hypothalamic Nuclei"]
            }
        ]
    },
    "Agency": {
        "color": "#82D1A1",
        "description": "Changes in the sense of agency, characterized by feeling that thoughts or actions are not self-generated or under one’s control, experiencing an urge to act, forced thinking, or sensing resistance to a planned action.",
        "regions": ["Right Angular Gyrus", "Temporoparietal Junction (TPJ)", "Inferior Parietal Lobule (IPL)", "Premotor Cortex", "Pre-SMA"],
        "subdomains": [],
        "response_types": {
            "Autoscopic Displacement": "A sense of displacement or duplication of the self in space, often with an illusory spatial separation from the body."
        },
        "sites": ["Right TPJ"]
    },
    "Consciousness": {
        "color": "#4F75A8",
        "description": "Responses classified as altered consciousness/awareness included loss of consciousness or impaired awareness, unconscious movements (i.e., movements occurring without awareness), or the erroneous impression of having spoken out loud.",
        "regions": ["Claustrum / External Capsule", "Intralaminar Thalamic Nuclei", "Precuneus", "Posterior Cingulate Cortex", "Default Mode Network"],
        "subdomains": [],
        "response_types": [],
        "sites": ["Claustrum / External Capsule"]
    },
    "No Effect": {
        "color": "#94A3B8",
        "description": "Stimulations explicitly reported as not evoking any functional response.",
        "regions": ["Silent Cortical Boundaries", "Non-Eloquent Association Cortex", "Subthreshold White Matter Tracts"],
        "subdomains": [],
        "response_types": [],
        "sites": ["Dorsolateral Prefrontal Cortex"]
    },
    "Other/ unclassifiable responses": {
        "color": "#D3D3D3",
        "description": "Stimulation responses that could not be assigned to any other domain.",
        "regions": [],
        "subdomains": [],
        "response_types": [],
        "sites": []
    }
}

 

# ==============================================================================
# DATASET GENERATION
# ==============================================================================
all_sites = []
site_idx = 1
random.seed(42) # Deterministic for consistent scientific coordinates

# Build clean taxonomy object for frontend consumption. Keep metadata structure for the UI,
# but do not synthesize stimulation entries from the static taxonomy when the source data is missing.
frontend_taxonomy = {}
for category, cat_data in taxonomy_schema.items():
    # Export top-level details and any response types defined directly on the domain.
    category_response_types, category_response_type_definitions = normalize_response_types(
        cat_data.get("response_types", [])
    )
    frontend_taxonomy[category] = {
        "color": cat_data["color"],
        "desc": cat_data["description"],
        "regions": cat_data.get("regions", []),
        "response_types": category_response_types,
        "subdomains": []
    }
    for sub in cat_data.get("subdomains", []):
        # Standardize response-type names and clean anatomical site labels for the website.
        response_types, response_type_definitions = normalize_response_types(sub.get("response_types", []))
        cleaned_sites = [clean_site_name(site) for site in sub.get("sites", []) if str(site).strip()]
        cleaned_sites = [site for site in cleaned_sites if site]

        # The front end uses "desc" for the definition shown in its taxonomy table.
        subdomain_record = {
            "name": sub["name"],
            "desc": sub["definition"],
            "hubs": sub.get("hubs", []),
            "response_types": response_types,
            "sites": cleaned_sites
        }
        if response_type_definitions:
            subdomain_record["response_type_definitions"] = response_type_definitions

        frontend_taxonomy[category]["subdomains"].append(subdomain_record)

if local_sample_path:
    # Load site rows only when a real workbook was found; otherwise keep the site list empty.
    all_sites = load_local_sample_sites(local_sample_path)
    if not all_sites:
        print("No valid workbook site rows loaded; leaving the website empty to surface the data issue.")
else:
    print("No local dataset workbook found; leaving the website empty to surface the data issue.")

print(f"Generated {len(all_sites)} total stimulation sites across {len(publications)} publications.")

# Put the site records, publication records, and taxonomy into one shared data object.
dataset = {
    "name": "StimBank Electrical Brain Stimulation Database (Harmonized Clinical Taxonomy)",
    "version": "2.0",
    "total_sites": len(all_sites),
    "total_publications": len(publications),
    "taxonomy": frontend_taxonomy,
    "publications": publications,
    "sites": all_sites
}

# Save JSON for Python/data consumers such as scripts and analysis tools.
json_path = os.path.join(data_dir, "ebs_data.json")
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(dataset, f, indent=2)

# Save the same data as JavaScript so browser pages can load it without a backend API.
js_path = os.path.join(data_dir, "ebs_dataset.js")
with open(js_path, "w", encoding="utf-8") as f:
    f.write("// StimBank Dataset & Taxonomy Export\n")
    f.write("window.EBS_DATASET = ")
    json.dump(dataset, f, indent=2)
    f.write(";\n")

print(f"Successfully saved clean dataset and taxonomy to:\n  - {json_path}\n  - {js_path}")
