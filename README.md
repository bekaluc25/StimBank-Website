# EBSBank: Electrical Brain Stimulation Database & 3D MNI Explorer

Welcome to **EBSBank**! This open-source platform hosts an interactive database and 3D stereotaxic explorer for human electrical brain stimulation (EBS) sites, evoked behavioral and sensory responses, and published neurosurgical literature.

Inspired by and designed to complement [LesionBank.org](https://lesionbank.org), EBSBank translates intracranial functional mapping findings (sEEG, subdural ECoG, awake craniotomy DES, and DBS) into standard **MNI152 stereotaxic coordinate space**.

---

## Key Features

1. **Interactive 3D MNI Brain Viewer (`viewer.html`)**:
   - WebGL 3D cortical surface rendering in standard MNI152 space.
   - Interactive camera rotation, zoom, and pan with presets (Left lateral, Right lateral, Superior dorsal, Anterior frontal, Posterior occipital, Inferior ventral).
   - Stimulation sites plotted as 3D spheres at exact $(X, Y, Z)$ coordinates with glowing category colors.
   - Real-time hover tooltips and clinical inspection modals.
   - Interactive hemisphere visibility toggles and glass brain opacity slider.

2. **Categorized Brain Responses & Demographics Homepage (`index.html`)**:
   - Interactive visual cards exploring the 8 primary brain response categories:
     - *Motor*, *Somatosensory*, *Language/Speech*, *Visual*, *Auditory*, *Affective/Emotional*, *Autonomic*, and *Cognitive/Memory*.
   - Dynamic spotlight with anatomical hubs, common effects, and MNI bounds.
   - **Research Literature Demographics Figures**:
     - Global research map/bar chart by country of origin.
     - Patient clinical populations and pathologies breakdown.
     - EBS surgical procedure distribution (sEEG, ECoG, DES, DBS).
     - Response category polar area chart.

3. **Database & Multi-attribute Filter Explorer (`explorer.html`)**:
   - Multi-attribute faceted filtering:
     - Filter by **Response Category** and **Evoked Effect**
     - Filter by **Clinical Pathology**
     - Filter by **EBS Procedure** (sEEG, ECoG, DES, DBS)
     - Filter by **Hemisphere** (Left / Right)
   - Live result counter (`Showing X of Y sites`).
   - Fast DataTables search, sort, and pagination.
   - Direct "View in 3D" link for any record.
   - Export filtered query results to CSV.

4. **Excel / CSV Dataset Importer (`importer.html`)**:
   - Easily drag & drop your own Excel spreadsheet (`.xlsx`, `.xls`) or CSV.
   - Client-side column mapping for MNI coordinates $(X, Y, Z)$, anatomical region labels, and responses.
   - Instant live preview in the 3D MNI brain viewer and database table without backend server setup.

5. **Methods & Safety Documentation (`about.html`)**:
   - Standard MNI152 stereotaxic space guidelines.
   - Clinical stimulation safety parameters (Shannon limit).
   - Review of sEEG, ECoG, DES, and DBS paradigms.

---

## Getting Started

### Option 1: Run with Local Python Server (Recommended)
From the project folder, simply run:

```bash
python3 serve.py
```

Then open your browser to:
- **Home**: [http://localhost:8080/index.html](http://localhost:8080/index.html)
- **3D Viewer**: [http://localhost:8080/viewer.html](http://localhost:8080/viewer.html)
- **Explorer**: [http://localhost:8080/explorer.html](http://localhost:8080/explorer.html)
- **Excel Importer**: [http://localhost:8080/importer.html](http://localhost:8080/importer.html)

### Option 2: Open Directly in Any Web Browser
Because all assets, styles, and datasets are self-contained and loaded via robust client-side scripts, you can also double-click `index.html` to open it directly in Chrome, Safari, Firefox, or Edge!

---

## Directory Structure

```
ebs-bank/
├── index.html               # Interactive Home & Demographics Figures
├── viewer.html              # 3D MNI Brain Viewer with OrbitControls
├── explorer.html            # Database Table with Faceted Filters
├── importer.html            # Drag-and-drop Excel (.xlsx) Dataset Loader
├── about.html               # Methods, Coordinate Systems & Safety Docs
├── serve.py                 # Lightweight Python HTTP server
├── generate_dataset.py      # Dataset generator script
├── data/
│   ├── ebs_data.json        # 135 stimulation sites & 22 publications in JSON
│   └── ebs_dataset.js       # Client-side JavaScript dataset wrapper
└── static/
    ├── css/
    │   └── ebs_custom.css   # Custom LesionBank-inspired stylesheet
    ├── js/
    │   ├── mni_brain_mesh.js # MNI152 parametric cortical geometry builder
    │   └── brain_viewer.js   # Three.js 3D Brain Viewer engine
    └── images/
        └── logo.svg         # EBSBank stylized brain logo
```
