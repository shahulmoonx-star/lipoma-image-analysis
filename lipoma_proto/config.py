"""Central settings for the lipoma prototype: paths, class merging and body regions."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DATASET_DIR = ROOT / "dataset"            # the author's original collection - never modified
CURATED_DIR = ROOT / "dataset_curated"        # cleaned, documented, publication-ready copy
DATA_DIR = ROOT / "data"
ARTIFACT_DIR = ROOT / "artifacts"
MODELS_DIR = ROOT / "models"
OUTPUT_DIR = ROOT / "outputs"

MODALITY_FILE = DATA_DIR / "modality_annotations.csv"
KNOWLEDGE_FILE = Path(__file__).resolve().parent / "knowledge_base.json"
MODEL_FILE = ARTIFACT_DIR / "lipoma_model.joblib"
FEATURE_CACHE = ARTIFACT_DIR / "features_cache.npz"

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
VIDEO_EXT = {".mp4", ".avi", ".mov", ".mkv"}

HF_CACHE_DIR = MODELS_DIR / "hf"              # BiomedCLIP weights are downloaded here on the first run

# BiomedCLIP: a vision-language model pre-trained on 15 million figure-caption pairs from PubMed Central.
# Selected after comparing DenseNet-121, DINOv2, ConvNeXt, CLIP ViT-L, SigLIP 2 and Rad-DINO.
BACKBONE = "biomedclip"
BIOMEDCLIP_ID = "hf-hub:microsoft/BiomedCLIP-PubMedBERT_256-vit_base_patch16_224"
IMG_SIZE = 224
LOGREG_C = 0.05            # location head
MODALITY_C = 0.3           # imaging-type head
# The location head is combined with BiomedCLIP's zero-shot text match ("a CT scan showing a gastric lipoma"):
#   score(class) = log p_classifier(class) + TEXT_PRIOR_WEIGHT * log p_text(class)
TEXT_PRIOR_WEIGHT = 0.3
TEXT_PRIOR_TEMP = 50.0
TEXT_TEMPLATES = ["{}", "a radiology image of a {}", "a CT scan showing a {}", "an MRI showing a {}",
                  "medical imaging of a {}", "a fat-containing lesion: {}"]

# Image matching (lipoma_proto/matching.py). Fast path: perceptual hash within this many bits (different
# stored images are >= 37 of 256 bits apart). Otherwise the most similar candidates are checked with keypoints:
# copies keep 60+ consistent keypoints, different pictures at most 14.
KNOWN_IMAGE_HASH_BITS = 20
MATCH_CANDIDATES = 8
MATCH_MIN_INLIERS = 30

# Folders that describe the same clinical entity (the dataset contains the very same
# images under both names), so they are merged into one class.
MERGE_CLASSES = {
    "inguinal canal lipoma": "inguinal canal / peritesticular lipoma",
    "peritesticular lipoma": "inguinal canal / peritesticular lipoma",
}

# A class needs at least this many distinct images to be trained / evaluated.
MIN_IMAGES_PER_CLASS = 3

MODALITY_NAMES = {
    "MR": "MRI",
    "CT": "CT",
    "US": "Ultrasound",
    "XR": "X-ray",
    "MG": "Mammography",
}

# Body region of each (merged) class; used for the coarse "where in the body" result.
REGION_OF_CLASS = {
    "cerebellopontine angle lipoma": "Brain / skull / scalp",
    "choroid plexus lipoma": "Brain / skull / scalp",
    "intracranial osteolipoma": "Brain / skull / scalp",
    "pericallosal lipoma": "Brain / skull / scalp",
    "quadrigeminal cistern lipoma": "Brain / skull / scalp",
    "subgaleal lipoma": "Brain / skull / scalp",
    "suprasellar cistern lipoma": "Brain / skull / scalp",
    "parotid lipoma": "Head & neck",
    "filar lipoma": "Spine",
    "cardiac lipoma": "Chest",
    "pericardial lipoma": "Chest",
    "mediastinal lipoma": "Chest",
    "endobronchial lipoma": "Chest",
    "pleural lipoma": "Chest",
    "chest wall lipoma": "Chest",
    "esophageal lipoma": "Chest",
    "breast lipoma": "Breast",
    "adrenal lipoma": "Abdomen",
    "gastric lipoma": "Abdomen",
    "hepatic lipoma": "Abdomen",
    "intestinal lipoma": "Abdomen",
    "mesenteric lipoma": "Abdomen",
    "pancreatic lipoma": "Abdomen",
    "paracaval lipoma": "Abdomen",
    "inguinal canal / peritesticular lipoma": "Groin / genital",
    "intramuscular lipoma": "Muscle / bone (limbs & trunk)",
    "intermuscular lipoma": "Muscle / bone (limbs & trunk)",
    "intraosseous lipoma": "Muscle / bone (limbs & trunk)",
    "parosteal lipoma": "Muscle / bone (limbs & trunk)",
}


def canonical_label(raw_label: str) -> str:
    """Map a raw folder / filename label to the merged class name."""
    return MERGE_CLASSES.get(raw_label, raw_label)


def region_of(label: str) -> str:
    return REGION_OF_CLASS.get(label, "Other")

