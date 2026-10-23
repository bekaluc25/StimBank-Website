import csv
import os
import re
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd
import seaborn as sns

if os.environ.get("DISPLAY", "") == "" and sys.platform != "win32":
    matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Patch

try:
    from IPython.display import display
except ImportError:  # pragma: no cover
    def display(obj):
        print(obj)

# Local output directory for generated figures. This avoids depending on a personal
# OneDrive path, which is often not available on another machine.
FIGURE_DIR = Path(__file__).resolve().parent / "figures"
FIGURE_DIR.mkdir(exist_ok=True)
SAVE_PATH = FIGURE_DIR

## paths
EBS_path_zoe = r"/Users/cristina/Partners HealthCare Dropbox/Christian Bekalu/Zoe_Garance_Stimbank/EBS_version3_stim_verified.xlsx"
EBS_path_garance = r"/Users/cristina/Partners HealthCare Dropbox/Christian Bekalu/Zoe_Garance_Stimbank/Data_coordinates_reconsctruction.xlsx"

def load_excel_file(path):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Required Excel file not found: {path}\n"
            "Update the paths at the top of generate_figures.py to point to your local data files."
        )

    if os.path.getsize(path) == 0:
        print(f"Warning: {path} is empty; skipping this file.")
        return pd.DataFrame()

    try:
        return pd.read_excel(path)
    except ValueError as exc:
        raise ValueError(
            f"Could not read {path}. Ensure it is a valid Excel file and not an empty or corrupted workbook."
        ) from exc

EBS_zoe = load_excel_file(EBS_path_zoe)
EBS_garance = load_excel_file(EBS_path_garance)

print(EBS_zoe.shape)
print(EBS_garance.shape)

save_path = SAVE_PATH

### Descriptive stats: 
columns_of_interest = [
    "Publication",
    "Region",
    "Pathology",
    "EBS procedure",
    "Type of coordinates",
    "Sample size",
    "Nb patients included",
    "Patient ID",
    "Age (years)",
    "Sex",
    "Handedness", 
    "Article"
]

frames = []
for frame in [EBS_zoe, EBS_garance]:
    if frame.empty:
        continue
    available_columns = [col for col in columns_of_interest if col in frame.columns]
    if not available_columns:
        continue
    frames.append(frame[available_columns])

if not frames:
    raise ValueError(
        "No usable data found in the input Excel files. Check that the workbook paths are valid and contain the expected columns."
    )

EBS = pd.concat(frames, ignore_index=True)

# Convert patient counts to numeric and keep one value per unique study/publication.
# Summing across all rows in the workbook overcounts because the same study appears
# many times in the Excel sheet. Using the first valid value per publication is more
# faithful to the study-level patient count.
if "Nb patients included" in EBS.columns:
    EBS["Nb patients included"] = (
        EBS["Nb patients included"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.replace(" ", "", regex=False)
        .apply(lambda x: pd.to_numeric(x, errors="coerce"))
    )

    study_patient_totals = (
        EBS.groupby("Publication", dropna=False)["Nb patients included"]
        .first()
        .dropna()
        .reset_index(name="patients_included_total")
    )

    total_patients_included = int(study_patient_totals["patients_included_total"].sum())
    total_studies_with_patient_data = int(
        study_patient_totals["patients_included_total"].notna().sum()
    )

    print("Total patients included across unique studies:", total_patients_included)
    print("Unique studies with patient counts:", total_studies_with_patient_data)

print(EBS.shape)

# ------------------ Plot the number of unique articles per year ---------------------------------

# Clean column names
EBS.columns = EBS.columns.str.replace("\xa0", " ", regex=False).str.strip()

# 1. Count unique articles
n_articles = EBS["Publication"].nunique()

print("Number of unique articles:", n_articles)

# 2. Extract publication year
EBS["Publication_year"] = (
    EBS["Publication"]
    .astype("string")
    .str.extract(r"(\d{4})", expand=False)
)

# Extract author name
EBS["Publication_author"] = (
    EBS["Publication"]
    .astype("string")
    .str.replace(r",?\s*\d{4}.*$", "", regex=True)
    .str.strip()
)

# 3. Keep one row per unique article
articles_unique = (
    EBS[["Publication", "Publication_author", "Publication_year"]]
    .drop_duplicates(subset=["Publication"])
)

# Count articles for which the publication year was successfully extracted
n_articles_with_year = articles_unique["Publication_year"].notna().sum()

print("Number of unique articles with a successfully extracted year:",
      n_articles_with_year)

print("Number of unique articles without an extracted year:",
      n_articles - n_articles_with_year)

# Display unique publications with their extracted author and year
display(
    articles_unique[
        ["Publication", "Publication_author", "Publication_year"]
    ].sort_values("Publication_year")
)

# 4. Count unique articles per publication year
articles_per_year = (
    articles_unique
    .dropna(subset=["Publication_year"])
    .groupby("Publication_year")
    .size()
    .sort_index()
)

print("Number of unique articles per year:")
display(articles_per_year)

# 5. Plot the number of unique articles per year
fig, ax = plt.subplots(figsize=(12, 6))

years = articles_per_year.index.astype(int)
values = articles_per_year.values

ax.bar(
    years,
    values,
    color="sandybrown",
    edgecolor="firebrick",
    linewidth=1,
    zorder=2
)

# Number of studies above each bar
for year, value in zip(years, values):
    ax.text(
        year,
        value + 0.3,
        str(value),
        ha="center",
        va="bottom",
        fontsize=10
    )

# Horizontal grid lines
for y in [6, 12, 18]:
    ax.axhline(
        y=y,
        color="lightgray",
        linestyle="--",
        linewidth=0.6,
        zorder=0
    )

ax.set_xlabel("Publication year")
ax.set_ylabel("Number of studies")

ax.set_yticks(range(2, 19, 2))
ax.set_ylim(0, 20)
ax.set_xticks(years)

# Labels:
# - 1991, 1994, 1996
# - then every 5 years from 2000 onwards
label_years = {1991, 1994, 1996}

label_years.update(
    year for year in years
    if year >= 2000 and year % 5 == 0
)

ax.set_xticklabels([
    str(year) if year in label_years else ""
    for year in years
])

ax.tick_params(
    axis="x",
    which="major",
    length=4,
    width=0.8
)

# Keep only X and Y axes
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

plt.tight_layout()
plt.savefig("figures/unique_articles_per_year.png", dpi=200, bbox_inches="tight")
plt.show() 

# ============================================================
# NUMBER OF STUDIES PER COUNTRY
# ============================================================

def extract_country(region):
    if pd.isna(region):
        return np.nan

    region = str(region).strip()

    # Keep only the country before "-", "/" or "—"
    country = re.split(r"\s*[-/—]\s*", region)[0].strip()

    return country


# Extract country from Region
EBS["Country"] = EBS["Region"].apply(extract_country)

# Keep one row per study
studies_country = (
    EBS[["Publication", "Country"]]
    .dropna(subset=["Publication", "Country"])
    .drop_duplicates(subset=["Publication", "Country"])
)

# Count studies per country
studies_per_country = (
    studies_country
    .groupby("Country")
    .size()
    .sort_values(ascending=False)
)

# ============================================================
# UNIFY COUNTRY NAMES
# ============================================================

country_mapping = {
    "USA": "United States of America",
    "Tokyo": "Japan",
    "UK": "United Kingdom"
}

EBS["Country"] = EBS["Country"].replace(country_mapping)

# Recalculate studies per country
studies_per_country = (
    EBS[["Publication", "Country"]]
    .dropna(subset=["Publication", "Country"])
    .drop_duplicates(subset=["Publication", "Country"])
    .groupby("Country")
    .size()
    .sort_values(ascending=False)
)

print("Number of studies per country:")
display(studies_per_country)

print("Total number of countries:", studies_per_country.size)
print("Total studies across countries:", studies_per_country.sum())

# ============================================================
# PIE CHART
# ============================================================

country_plot = studies_per_country.copy()

# Group countries with fewer than 2 studies
other = country_plot[country_plot < 2].sum()
country_plot = country_plot[country_plot >= 2]

if other > 0:
    country_plot["Other"] = other

fig, ax = plt.subplots(figsize=(8, 8))

ax.pie(
    country_plot.values,
    labels=country_plot.index,
    autopct="%1.1f%%",
    startangle=90
)

ax.set_title("Distribution of studies by country")

plt.tight_layout()
plt.savefig("figures/Pie_Chart_distribution_studies_per_country.png", dpi=200, bbox_inches="tight")
plt.show()

# ============================================================
# PIE CHART
# ============================================================

country_plot = studies_per_country.copy()

# Group countries with fewer than 2 studies
other = country_plot[country_plot < 2].sum()
country_plot = country_plot[country_plot >= 2]

if other > 0:
    country_plot["Other"] = other


# Show percentage only if >= 3%
def autopct_threshold(pct):
    return f"{pct:.1f}%" if pct >= 3 else ""


# Colormap
cmap = plt.get_cmap("tab20")
colors = cmap(np.linspace(0, 1, len(country_plot)))


fig, ax = plt.subplots(figsize=(10, 8))

wedges, texts, autotexts = ax.pie(
    country_plot.values,
    labels=None,
    autopct=autopct_threshold,
    startangle=90,
    colors=colors
)

# Legend
ax.legend(
    wedges,
    country_plot.index,
    title="Country",
    loc="center left",
    bbox_to_anchor=(1, 0.5)
)

ax.set_title("Distribution of studies by country")

plt.tight_layout()
plt.savefig("figures/Pie_Chart_distribution_studies_per_country.png", dpi=200, bbox_inches="tight")
plt.show()
# ============================================================
# WORLD MAP — % OF STUDIES BY COUNTRY
# ============================================================

# Total number of studies counted across countries
total_studies_country = studies_per_country.sum()

# DataFrame
country_data = studies_per_country.reset_index()
country_data.columns = ["Country", "Studies"]

# Percentage
country_data["Percentage"] = (
    country_data["Studies"] / total_studies_country * 100
)

# Load world map
world = gpd.read_file(
    "https://naturalearth.s3.amazonaws.com/110m_cultural/ne_110m_admin_0_countries.zip"
)

# Adapt country names
world["Country_clean"] = world["ADMIN"]

# Merge
world = world.merge(
    country_data,
    left_on="Country_clean",
    right_on="Country",
    how="left"
)

# Plot
fig, ax = plt.subplots(figsize=(14, 7))

world.plot(
    column="Percentage",
    cmap="YlOrRd",
    linewidth=0.3,
    edgecolor="lightgray",
    legend=True,
    ax=ax,
    missing_kwds={
        "color": "lightgray"
    }
)

ax.set_title("Geographical distribution of EBS studies", fontsize=14)
ax.axis("off")

plt.tight_layout()
plt.savefig("figures/percentage_studies_per_country.png", dpi=200, bbox_inches="tight")
plt.show()

# ============================================================
# WORLD MAP — PROPORTIONAL CIRCLES + %
# ============================================================

# Data
country_data = studies_per_country.reset_index()
country_data.columns = ["Country", "Studies"]

# Percentage of studies
total = country_data["Studies"].sum()

country_data["Percentage"] = (
    country_data["Studies"] / total * 100
)

# World map
world = gpd.read_file(
    "https://naturalearth.s3.amazonaws.com/110m_cultural/ne_110m_admin_0_countries.zip"
)

# Merge
world = world.merge(
    country_data,
    left_on="ADMIN",
    right_on="Country",
    how="left"
)

# Centroids for circles
world["centroid"] = world.geometry.representative_point()

# Plot
fig, ax = plt.subplots(figsize=(15, 8))

# Countries
world.plot(
    ax=ax,
    color="whitesmoke",
    edgecolor="lightgray",
    linewidth=0.5
)

# Only countries with studies
data = world.dropna(subset=["Studies"]).copy()

# Proportional circles
ax.scatter(
    data["centroid"].x,
    data["centroid"].y,
    s=data["Studies"] * 25,
    alpha=0.65,
    edgecolor="black",
    linewidth=0.5
)

# Percentage labels
for _, row in data.iterrows():
    ax.text(
        row["centroid"].x,
        row["centroid"].y,
        f'{row["Percentage"]:.1f}%',
        ha="center",
        va="center",
        fontsize=8
    )

ax.set_title(
    "Geographical distribution of EBS studies",
    fontsize=15
)

ax.axis("off")

plt.tight_layout()
plt.savefig("figures/world_map_distribution.png", dpi=200, bbox_inches="tight")
plt.show()

# ============================================================
# LOLLIPOP — STUDIES BY COUNTRY
# ============================================================

data = studies_per_country.sort_values(ascending=True)

# Percentage
total = data.sum()
percentage = data / total * 100

fig, ax = plt.subplots(figsize=(10, 7))

# Lines
ax.hlines(
    y=data.index,
    xmin=0,
    xmax=data.values,
    linewidth=1.5,
    color="lightgray"
)

# Dots
ax.scatter(
    data.values,
    data.index,
    s=70,
    color="steelblue",
    zorder=3
)

# Percentage labels
for country, value in data.items():
    pct = percentage[country]
    ax.text(
        value + 1,
        country,
        f"{pct:.1f}%",
        va="center",
        fontsize=9
    )

# Labels
ax.set_xlabel("Number of studies")
ax.set_ylabel("")

ax.set_title(
    "Distribution of EBS studies by country",
    fontsize=14
)

# Clean style
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.spines["left"].set_visible(False)

ax.tick_params(axis="y", length=0)

plt.tight_layout()
plt.savefig("figures/studies_per_country.png", dpi=200, bbox_inches="tight")
plt.show()

# ============================================================
# NUMBER OF STUDIES PER EBS PROCEDURE
# ============================================================

def classify_procedure(group):
    procedures = set()

    for value in group.dropna().astype(str).str.lower():
        if "dbs" in value:
            procedures.add("DBS")
        if "awake craniotomy" in value:
            procedures.add("Awake")
        if "asleep craniotomy" in value:
            procedures.add("Asleep")
        if "ecog" in value:
            procedures.add("ECoG")
        if "seeg" in value:
            procedures.add("SEEG")

    if len(procedures) > 1:
        return "Multiple procedure"
    if len(procedures) == 1:
        return procedures.pop()
    return np.nan


# Classify each study
study_procedure = (
    EBS.groupby("Publication")["EBS procedure"]
    .apply(classify_procedure)
    .reset_index(name="Procedure")
)

# Count procedures
counts = study_procedure["Procedure"].value_counts()

awake = counts.get("Awake", 0)
asleep = counts.get("Asleep", 0)

# Category
final_counts = pd.Series({
    "SEEG": counts.get("SEEG", 0),
    "ECoG": counts.get("ECoG", 0),
    "DBS": counts.get("DBS", 0),
    "Multiple procedure": counts.get("Multiple procedure", 0),
    "Craniotomy": awake + asleep
}).sort_values(ascending=False)


## check: 

total_studies = EBS["Publication"].nunique()

print("========================================")
print("EBS PROCEDURE ANALYSIS")
print("========================================")
print("\nTotal number of unique studies:",total_studies)
print("\nFinal number of studies per procedure:")
display(final_counts)
print("\nSum of final categories:",final_counts.sum())
print("\nDifference:",total_studies - final_counts.sum())

# ============================================================
# PLOT
# ============================================================

colors = {
    "SEEG": plt.cm.tab10(0),
    "ECoG": plt.cm.tab10(1),
    "DBS": plt.cm.tab10(2),
    "Multiple procedure": plt.cm.tab10(3),
    "Awake": plt.cm.tab10(4),
    "Asleep": plt.cm.tab10(5)
}


fig, ax = plt.subplots(figsize=(7, 4))

x = np.arange(len(final_counts)) * 0.7
width = 0.45

for i, category in enumerate(final_counts.index):

    if category == "Craniotomy":

        ax.bar(
            i * 0.7,
            awake,
            width=width,
            color=colors["Awake"]
        )

        ax.bar(
            i * 0.7,
            asleep,
            width=width,
            bottom=awake,
            color=colors["Asleep"]
        )

    else:

        ax.bar(
            i * 0.7,
            final_counts[category],
            width=width,
            color=colors[category]
        )

for i, value in enumerate(final_counts):

    ax.text(
        i * 0.7,
        value + 1,
        str(int(value)),
        ha="center",
        va="bottom",
        fontsize=10
    )

ax.set_xticks(x)
ax.set_xticklabels(final_counts.index)

ax.set_xlabel("EBS procedure")
ax.set_ylabel("Number of studies")
ax.set_title("Number of studies by EBS procedure")

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

legend_elements = [
    Patch(facecolor=colors["Awake"], label="Awake"),
    Patch(facecolor=colors["Asleep"], label="Asleep")
]

ax.legend(
    handles=legend_elements,
    title="Craniotomy",
    frameon=False
)

plt.tight_layout()
plt.savefig("figures/study_distribution_per_procedure.png", dpi=200, bbox_inches="tight")
plt.show()