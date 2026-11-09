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
    """Return the first non-empty local sample file we should use as the input dataset."""
    candidates = [
        '/Users/cristina/Partners HealthCare Dropbox/Christian Bekalu/Zoe_Garance_Stimbank/website/Sample_Christian_2.xlsx',
        os.path.join(data_dir, 'Sample_Christian_2.xlsx'),
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate) and os.path.getsize(candidate) > 0:
            return candidate
    return None

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
    if not excel_path or not os.path.exists(excel_path):
        return []

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
    idx = {name: i for i, name in enumerate(header)}

    publications = []
    seen = set()

    for row in rows[1:]:
        if not row or not any(cell is not None and str(cell).strip() for cell in row):
            continue

        publication_label = row[idx['Publication']] if 'Publication' in idx and idx['Publication'] < len(row) else row[0]
        article_label = row[idx['Article']] if 'Article' in idx and idx['Article'] < len(row) else publication_label
        label = str(article_label or publication_label or '').strip()
        if not label:
            continue

        key = label
        if key in seen:
            continue
        seen.add(key)

        pathology = str((row[idx['Pathology']] if 'Pathology' in idx and idx['Pathology'] < len(row) else 'Not specified') or 'Not specified').strip() or 'Not specified'
        procedure = str((row[idx['EBS procedure']] if 'EBS procedure' in idx and idx['EBS procedure'] < len(row) else 'Not specified') or 'Not specified').strip() or 'Not specified'
        sample_size = row[idx['Sample size']] if 'Sample size' in idx and idx['Sample size'] < len(row) else 0
        try:
            sample_size_value = int(float(str(sample_size).replace(',', '')))
        except Exception:
            sample_size_value = 0

        year_match = re.search(r'(19|20)\d{2}', label)
        year = int(year_match.group(0)) if year_match else 0

        publications.append({
            'id': f'LOCAL{len(publications) + 1:03d}',
            'authors': label[:120],
            'year': year,
            'title': label,
            'journal': 'Local sample dataset',
            'country': str((row[idx['Region']] if 'Region' in idx and idx['Region'] < len(row) else 'Local dataset') or 'Local dataset').strip() or 'Local dataset',
            'institution': 'Local sample dataset',
            'sample_size': sample_size_value,
            'patient_population': pathology,
            'procedure_type': procedure,
            'doi': '',
            'pmid': ''
        })

    return publications


def safe_float(value):
    """Parse a numeric value from the Excel workbook and return None if invalid."""
    if value is None:
        return None
    try:
        return float(str(value).replace(',', '').strip())
    except (TypeError, ValueError):
        return None


def load_local_sample_sites(excel_path):
    """Load site-level entries directly from the workbook.

    This is the strict, no-fallback source. If the workbook lacks the required
    coordinate columns or the row format is invalid, return an empty list so the
    site remains empty instead of auto-populating placeholder values.
    """
    if not excel_path or not os.path.exists(excel_path):
        return []

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
    idx = {name: i for i, name in enumerate(header)}
    required = [
        'Side of stimulation',
        'EBS coordinates (MNI space) x',
        'EBS coordinates (MNI space) y',
        'EBS coordinates (MNI space) z',
    ]
    if not all(key in idx for key in required):
        return []

    sites = []
    domain_name_map = {
        'Sensory-Perceptual': 'Sensory',
        'Affective': 'Affective',
        'Autonomic': 'Autonomic',
        'Cognitive/language': 'Cognitive',
        'Motor': 'Motor',
        'Altered consciousness/awareness': 'Consciousness',
        'Agency': 'Agency',
        'No effect': 'No Effect',
        'Other/unclassifiable': 'Other/ unclassifiable responses',
    }

    for row_index, row in enumerate(rows[1:], start=2):
        if not row or not any(cell is not None and str(cell).strip() for cell in row):
            continue

        side = str(row[idx['Side of stimulation']] or '').strip().lower()
        if side not in {'left', 'right'}:
            continue

        x = safe_float(row[idx['EBS coordinates (MNI space) x']])
        y = safe_float(row[idx['EBS coordinates (MNI space) y']])
        z = safe_float(row[idx['EBS coordinates (MNI space) z']])
        if x is None or y is None or z is None:
            continue

        # 
        category_labels = []
        for col_index in range(7, min(79, len(header))):
            value = row[col_index]
            if value is None:
                continue
            cell_name = str(header[col_index]).strip()
            if not cell_name:
                continue
            normalized_value = str(value).strip().lower()
            if value is True or value == 1 or normalized_value in {'true', '1', '1.0'}:
                active_flag_names.append(cell_name)

        if not active_flag_names:
            continue

        domain_name = None
        subdomain_name = None
        response_types = []
        for cell_name in active_flag_names:
            if cell_name in domain_name_map:
                if domain_name is None:
                    domain_name = cell_name
                elif subdomain_name is None:
                    subdomain_name = cell_name
            else:
                response_types.append(cell_name)

        if domain_name is None:
            continue

        category = domain_name_map.get(domain_name, domain_name)

        publication = str(row[idx['Publication']] if 'Publication' in idx and idx['Publication'] < len(row) else '').strip() or 'Unknown publication'
        region = str(row[idx['Site of EBS evoking a response']] if 'Site of EBS evoking a response' in idx and idx['Site of EBS evoking a response'] < len(row) else row[idx['Brain area explored']] if 'Brain area explored' in idx and idx['Brain area explored'] < len(row) else 'Unknown region').strip() or 'Unknown region'
        effect = str(row[idx['Phenomenological description']] if 'Phenomenological description' in idx and idx['Phenomenological description'] < len(row) else row[idx['Site of EBS evoking a response']] if 'Site of EBS evoking a response' in idx and idx['Site of EBS evoking a response'] < len(row) else 'Stimulated site').strip() or 'Stimulated site'
        pathology = str(row[idx['Pathology']] if 'Pathology' in idx and idx['Pathology'] < len(row) else 'Unknown pathology').strip() or 'Unknown pathology'
        procedure = str(row[idx['EBS procedure']] if 'EBS procedure' in idx and idx['EBS procedure'] < len(row) else 'Unknown procedure').strip() or 'Unknown procedure'
        age = safe_float(row[idx['Age (years)']] if 'Age (years)' in idx and idx['Age (years)'] < len(row) else None)
        sex = str(row[idx['Sex']] if 'Sex' in idx and idx['Sex'] < len(row) else 'Unknown').strip() or 'Unknown'

        sites.append({
            'id': f'WORKBOOK{len(sites) + 1:03d}',
            'patient_id': str(row[idx['Patient ID']] if 'Patient ID' in idx and idx['Patient ID'] < len(row) else f'ROW{row_index}').strip() or f'ROW{row_index}',
            'patient_display': str(row[idx['Patient ID']] if 'Patient ID' in idx and idx['Patient ID'] < len(row) else f'Row {row_index}').strip() or f'Row {row_index}',
            'category': category,
            'subcategory': subdomain_name or category,
            'domain': category,
            'subdomain': subdomain_name or category,
            'response_types': response_types,
            'effect': effect,
            'description': effect,
            'region': region,
            'hemisphere': 'L' if side == 'left' else 'R',
            'mni': [x, y, z],
            'procedure': procedure,
            'pathology': pathology,
            'frequency_hz': safe_float(row[idx['Stimulation parameters Frequency (Hz)']] if 'Stimulation parameters Frequency (Hz)' in idx and idx['Stimulation parameters Frequency (Hz)'] < len(row) else None),
            'current_ma': safe_float(row[idx['Stimulation parameters Intensity']] if 'Stimulation parameters Intensity' in idx and idx['Stimulation parameters Intensity'] < len(row) else None),
            'pulse_width_ms': safe_float(row[idx['Stimulation parameters  Pulse width (ms)']] if 'Stimulation parameters  Pulse width (ms)' in idx and idx['Stimulation parameters  Pulse width (ms)'] < len(row) else None),
            'bipolar': True,
            'pub_id': publication,
            'publication': {'title': publication, 'journal': 'Local workbook dataset'},
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
    frontend_taxonomy[category] = {
        "color": cat_data["color"],
        "desc": cat_data["description"],
        "regions": cat_data.get("regions", []),
        "subdomains": []
    }
    for sub in cat_data.get("subdomains", []):
        response_types, response_type_definitions = normalize_response_types(sub.get("response_types", []))
        cleaned_sites = [clean_site_name(site) for site in sub.get("sites", []) if str(site).strip()]
        cleaned_sites = [site for site in cleaned_sites if site]

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
    all_sites = load_local_sample_sites(local_sample_path)
    if not all_sites:
        print("No valid workbook site rows loaded; leaving the website empty to surface the data issue.")
else:
    print("No local dataset workbook found; leaving the website empty to surface the data issue.")

print(f"Generated {len(all_sites)} total stimulation sites across {len(publications)} publications.")

# Assemble finalized dataset object
dataset = {
    "name": "StimBank Electrical Brain Stimulation Database (Harmonized Clinical Taxonomy)",
    "version": "2.0",
    "total_sites": len(all_sites),
    "total_publications": len(publications),
    "taxonomy": frontend_taxonomy,
    "publications": publications,
    "sites": all_sites
}

# Write out JSON
json_path = os.path.join(data_dir, "ebs_data.json")
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(dataset, f, indent=2)

# Write out JS wrapper for standalone static consumption
js_path = os.path.join(data_dir, "ebs_dataset.js")
with open(js_path, "w", encoding="utf-8") as f:
    f.write("// StimBank Dataset & Taxonomy Export\n")
    f.write("window.EBS_DATASET = ")
    json.dump(dataset, f, indent=2)
    f.write(";\n")

print(f"Successfully saved clean dataset and taxonomy to:\n  - {json_path}\n  - {js_path}")
