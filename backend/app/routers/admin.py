"""Admin management endpoints."""

import logging
import random
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends

from app.auth.dependencies import require_role
from app.services.cosmos_db import cosmos_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats")
async def get_stats(
    user: dict[str, Any] = Depends(require_role("Admin")),
) -> dict[str, Any]:
    """Get overall system statistics. Admin only."""
    stats = await cosmos_service.get_stats()
    return stats


@router.get("/doctors")
async def list_doctors_with_stats(
    user: dict[str, Any] = Depends(require_role("Admin")),
) -> list[dict[str, Any]]:
    """List all doctors with their usage statistics. Admin only."""
    return await cosmos_service.get_doctors_with_stats()


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

SEED_DOCTORS = [
    {"name": "Dr. Sarah Chen", "specialty": "Diagnostic Radiology", "department": "Body Imaging"},
    {"name": "Dr. James Okafor", "specialty": "Neuroradiology", "department": "Neuro Imaging"},
    {"name": "Dr. Maria Rodriguez", "specialty": "Musculoskeletal Radiology", "department": "MSK Imaging"},
    {"name": "Dr. David Kim", "specialty": "Chest Radiology", "department": "Thoracic Imaging"},
    {"name": "Dr. Emily Watson", "specialty": "Breast Imaging", "department": "Women's Imaging"},
    {"name": "Dr. Raj Patel", "specialty": "Interventional Radiology", "department": "IR"},
    {"name": "Dr. Lisa Tanaka", "specialty": "Pediatric Radiology", "department": "Pediatric Imaging"},
    {"name": "Dr. Michael Brooks", "specialty": "Nuclear Medicine / PET", "department": "Nuclear Medicine"},
    {"name": "Dr. Amanda Foster", "specialty": "Emergency Radiology", "department": "Emergency Imaging"},
    {"name": "Dr. Carlos Mendez", "specialty": "Oncologic Imaging", "department": "Oncology Imaging"},
]

# Per-doctor style traits that affect report language
_STYLE_MAP: dict[str, dict[str, Any]] = {
    "Dr. Sarah Chen": {
        "tone": "concise_clinical",
        "abbreviation_map": {"WNL": "within normal limits", "LN": "lymph node"},
        "sample_phrases": [
            "No acute abnormality identified.",
            "Stable since prior comparison.",
            "Recommend clinical correlation.",
        ],
    },
    "Dr. James Okafor": {
        "tone": "academic_detailed",
        "abbreviation_map": {"FLAIR": "fluid-attenuated inversion recovery", "DWI": "diffusion-weighted imaging"},
        "sample_phrases": [
            "No evidence of acute intracranial process.",
            "Signal abnormality is nonspecific and may represent…",
            "Correlation with CSF studies is suggested.",
        ],
    },
    "Dr. Maria Rodriguez": {
        "tone": "structured_bullet",
        "abbreviation_map": {"ACL": "anterior cruciate ligament", "MCL": "medial collateral ligament"},
        "sample_phrases": [
            "- Intact menisci bilaterally.",
            "- No marrow edema.",
            "Recommend follow-up in 6 weeks if symptoms persist.",
        ],
    },
    "Dr. David Kim": {
        "tone": "narrative_thorough",
        "abbreviation_map": {"GGO": "ground-glass opacity", "PE": "pulmonary embolism"},
        "sample_phrases": [
            "The lungs are clear bilaterally without focal consolidation.",
            "Heart size is within normal limits. No pericardial effusion.",
            "Recommend follow-up chest CT in 3 months for indeterminate nodule.",
        ],
    },
    "Dr. Emily Watson": {
        "tone": "formal_protocol",
        "abbreviation_map": {"BI-RADS": "Breast Imaging Reporting and Data System"},
        "sample_phrases": [
            "Assessment: BI-RADS 2 — Benign finding.",
            "This is a negative mammogram.",
            "Routine annual screening mammography is recommended.",
        ],
    },
    "Dr. Raj Patel": {
        "tone": "procedural_concise",
        "abbreviation_map": {"Fr": "French (catheter size)", "DSA": "digital subtraction angiography"},
        "sample_phrases": [
            "Access obtained via right common femoral artery using modified Seldinger technique.",
            "No immediate complications. Patient tolerated the procedure well.",
            "Estimated blood loss: minimal.",
        ],
    },
    "Dr. Lisa Tanaka": {
        "tone": "gentle_descriptive",
        "abbreviation_map": {"AP": "anteroposterior"},
        "sample_phrases": [
            "Normal growth pattern for stated age.",
            "No acute osseous abnormality.",
            "Clinical correlation with growth charts is recommended.",
        ],
    },
    "Dr. Michael Brooks": {
        "tone": "quantitative_precise",
        "abbreviation_map": {"SUV": "standardized uptake value", "FDG": "fluorodeoxyglucose"},
        "sample_phrases": [
            "SUVmax of 4.2 is mildly hypermetabolic.",
            "No FDG-avid disease above or below the diaphragm.",
            "Compared to prior PET/CT, interval decrease in metabolic activity.",
        ],
    },
    "Dr. Amanda Foster": {
        "tone": "urgent_direct",
        "abbreviation_map": {"SDH": "subdural hematoma", "SAH": "subarachnoid hemorrhage"},
        "sample_phrases": [
            "CRITICAL FINDING communicated to ED physician.",
            "No acute intracranial hemorrhage.",
            "Recommend emergent neurosurgical consultation.",
        ],
    },
    "Dr. Carlos Mendez": {
        "tone": "longitudinal_comparative",
        "abbreviation_map": {"RECIST": "Response Evaluation Criteria in Solid Tumors"},
        "sample_phrases": [
            "Target lesion in segment 6 now measures 2.1 × 1.8 cm (previously 2.8 × 2.2 cm) — partial response per RECIST 1.1.",
            "No new sites of metastatic disease.",
            "Recommend continued current treatment regimen.",
        ],
    },
}

# Report templates keyed by (report_type, body_region)
_REPORT_TEMPLATES: list[dict[str, Any]] = [
    {
        "report_type": "CT",
        "body_region": "Abdomen",
        "input_text": "CT abdomen and pelvis with contrast. Liver appears normal. No biliary dilatation. Pancreas, spleen, and adrenals are unremarkable. Kidneys show a 3mm nonobstructing stone in the left kidney. No hydronephrosis. Bowel gas pattern is normal.",
        "findings": "Liver is normal in size and attenuation without focal lesion. No intra- or extra-hepatic biliary dilatation. Gallbladder is normal. Pancreas, spleen, and adrenal glands are unremarkable. A 3 mm nonobstructing calculus is present in the lower pole of the left kidney. No hydronephrosis. Normal bowel gas pattern. No free fluid.",
        "impressions": "1. Small nonobstructing left renal calculus.\n2. Otherwise unremarkable CT of the abdomen and pelvis.",
        "recommendations": "Clinical correlation. No follow-up imaging required unless symptoms change.",
    },
    {
        "report_type": "MRI",
        "body_region": "Brain",
        "input_text": "MRI brain with and without contrast. No acute infarct on DWI. No mass lesion. Mild periventricular white matter changes. Ventricles normal in size. No extra-axial fluid collection. Post-contrast no abnormal enhancement.",
        "findings": "No restricted diffusion to suggest acute infarct. No intracranial mass or mass effect. Mild scattered T2/FLAIR hyperintensities in periventricular white matter, nonspecific but likely reflecting chronic small vessel ischemic changes. Ventricles and sulci are normal in size and configuration. No extra-axial collection. No abnormal intracranial enhancement post gadolinium administration.",
        "impressions": "1. No acute intracranial abnormality.\n2. Mild nonspecific periventricular white matter changes, likely chronic microvascular.",
        "recommendations": "Clinical correlation with patient history. No urgent follow-up needed.",
    },
    {
        "report_type": "CT",
        "body_region": "Chest",
        "input_text": "CT chest with contrast for PE evaluation. No pulmonary embolism. Heart normal size. Lungs clear bilaterally. Small 4mm right lower lobe nodule. No pleural effusion. Mediastinal lymph nodes not enlarged. Thoracic aorta normal caliber.",
        "findings": "No filling defect within the pulmonary arteries to suggest pulmonary embolism. Heart is normal in size. Lungs are clear without consolidation or ground-glass opacity. A 4 mm solid nodule is noted in the right lower lobe (series 3, image 142). No pleural effusion. Mediastinal and hilar lymph nodes are within normal limits. Thoracic aorta is normal in caliber.",
        "impressions": "1. No pulmonary embolism.\n2. Incidental 4 mm right lower lobe pulmonary nodule.",
        "recommendations": "For the 4 mm nodule, follow-up CT in 12 months per Fleischner Society guidelines if no prior history of malignancy.",
    },
    {
        "report_type": "X-ray",
        "body_region": "Chest",
        "input_text": "PA and lateral chest radiograph. Heart size normal. Lungs clear. No pleural effusion. No pneumothorax. Osseous structures intact. Soft tissues unremarkable.",
        "findings": "PA and lateral views of the chest demonstrate normal cardiac silhouette. Lungs are clear without focal airspace disease. No pleural effusion or pneumothorax. Mediastinal contour is normal. Visualized osseous structures are intact.",
        "impressions": "No acute cardiopulmonary abnormality.",
        "recommendations": "None.",
    },
    {
        "report_type": "MRI",
        "body_region": "Spine",
        "input_text": "MRI lumbar spine without contrast. At L4-5 there is a 5mm broad-based disc protrusion causing mild bilateral foraminal narrowing. L5-S1 disc desiccation with small annular fissure. Conus medullaris terminates at L1 level. No compression fracture.",
        "findings": "L4-L5: Broad-based disc protrusion measuring approximately 5 mm in AP extent causing mild bilateral neural foraminal narrowing without significant central canal stenosis. L5-S1: Disc desiccation with small posterior annular fissure. No significant stenosis. Remaining lumbar levels are unremarkable. Conus medullaris terminates normally at the L1 level. Vertebral body heights and alignment are maintained. No compression fracture. Paraspinal soft tissues are normal.",
        "impressions": "1. L4-L5 broad-based disc protrusion with mild bilateral foraminal narrowing.\n2. L5-S1 degenerative disc disease with annular fissure.\n3. No compression fracture or spinal cord abnormality.",
        "recommendations": "Clinical correlation with symptoms. Consider conservative management. MRI with contrast if clinical concern for infection or neoplasm.",
    },
    {
        "report_type": "Ultrasound",
        "body_region": "Abdomen",
        "input_text": "Right upper quadrant ultrasound. Liver is normal in echotexture and size measuring 15 cm. No focal hepatic lesion. Gallbladder is distended with sludge but no gallstones. No gallbladder wall thickening. Common bile duct measures 4mm. Right kidney 11.2 cm with a simple cortical cyst measuring 2.3 cm. No hydronephrosis.",
        "findings": "Liver measures 15 cm, normal in echotexture without focal lesion. Gallbladder is distended with echogenic sludge; no discrete gallstones identified. Gallbladder wall measures 2 mm (normal). Common bile duct measures 4 mm (normal). Right kidney measures 11.2 cm with a simple-appearing cortical cyst in the upper pole measuring 2.3 cm. No hydronephrosis bilaterally.",
        "impressions": "1. Gallbladder sludge without cholelithiasis or cholecystitis.\n2. Simple right renal cortical cyst (2.3 cm) — Bosniak I.\n3. Normal liver.",
        "recommendations": "No emergent follow-up. Correlate with clinical symptoms.",
    },
    {
        "report_type": "PET",
        "body_region": "Whole Body",
        "input_text": "F-18 FDG PET/CT whole body. Known non-small cell lung cancer status post right upper lobectomy. No FDG-avid residual disease in the right hemithorax. Post-surgical changes noted. No hypermetabolic mediastinal or hilar lymphadenopathy. Liver, adrenals, and skeleton without FDG-avid metastatic disease. Physiologic FDG uptake in brain, myocardium, and urinary tract.",
        "findings": "Post-surgical changes in the right hemithorax without FDG-avid residual or recurrent disease. No hypermetabolic mediastinal or hilar lymphadenopathy. Liver is unremarkable without FDG-avid focal lesion. Bilateral adrenal glands are normal. No FDG-avid osseous metastatic disease. Physiologic biodistribution of FDG in the brain, myocardium, and urinary tract.",
        "impressions": "1. No evidence of FDG-avid recurrent or metastatic disease post right upper lobectomy for NSCLC.\n2. Post-surgical changes in the right hemithorax.",
        "recommendations": "Continue surveillance per oncology protocol. Recommend follow-up PET/CT in 6 months.",
    },
    {
        "report_type": "CT",
        "body_region": "Head",
        "input_text": "Non-contrast CT head for trauma evaluation. No acute intracranial hemorrhage. No skull fracture. Ventricles symmetric and normal size. Gray-white matter differentiation preserved. No midline shift. Paranasal sinuses clear. Mastoid air cells are clear.",
        "findings": "No acute intracranial hemorrhage, extra-axial collection, or mass effect. No skull fracture. Ventricular system is symmetric and normal in size. Gray-white matter differentiation is preserved. No midline shift. Paranasal sinuses and mastoid air cells are well aerated. Visualized orbits are unremarkable.",
        "impressions": "1. No acute intracranial abnormality.\n2. No skull fracture.",
        "recommendations": "Clinical correlation. Return to ED if symptoms worsen.",
    },
    {
        "report_type": "MRI",
        "body_region": "Lower Extremity",
        "input_text": "MRI right knee without contrast. ACL is intact. PCL is intact. Medial and lateral menisci are normal without tear. Medial and lateral collateral ligaments are intact. Mild joint effusion. No bone marrow edema. Patellar cartilage has grade 2 chondromalacia. Quadriceps and patellar tendons intact.",
        "findings": "ACL and PCL are intact with normal signal and morphology. Medial and lateral menisci demonstrate normal signal without evidence of tear. MCL and LCL are intact. Mild joint effusion is present. No bone marrow edema pattern. Grade 2 chondromalacia of the patellar cartilage with mild surface irregularity. Quadriceps and patellar tendons are intact. Baker's cyst is not identified.",
        "impressions": "1. Intact ACL, PCL, menisci, and collateral ligaments.\n2. Mild joint effusion.\n3. Grade 2 patellar chondromalacia.",
        "recommendations": "Conservative management with activity modification. Repeat imaging if symptoms worsen or do not improve in 6 weeks.",
    },
    {
        "report_type": "Ultrasound",
        "body_region": "Neck",
        "input_text": "Thyroid ultrasound. Right lobe measures 5.2 x 1.8 x 1.6 cm. Left lobe 4.8 x 1.7 x 1.5 cm. Isthmus 3mm. Right lobe contains a well-circumscribed anechoic cyst measuring 8mm. Left lobe has a 12mm predominantly solid hypoechoic nodule with internal vascularity. No calcifications. No suspicious cervical lymphadenopathy.",
        "findings": "Right thyroid lobe measures 5.2 × 1.8 × 1.6 cm with an 8 mm simple-appearing anechoic cyst. Left thyroid lobe measures 4.8 × 1.7 × 1.5 cm with a 12 mm predominantly solid hypoechoic nodule demonstrating internal vascularity on color Doppler. No microcalcifications or irregular margins. Isthmus measures 3 mm. No suspicious cervical lymphadenopathy.",
        "impressions": "1. Right thyroid simple cyst (8 mm) — benign.\n2. Left thyroid solid hypoechoic nodule (12 mm) — ACR TI-RADS 3 (mildly suspicious).",
        "recommendations": "FNA biopsy recommended for the left thyroid nodule per ACR TI-RADS guidelines (≥ 2.5 cm for TR3, but given vascularity, consider biopsy at 1.5 cm threshold). Follow-up ultrasound in 12 months if FNA is deferred.",
    },
]


def _apply_doctor_style(template: dict[str, Any], doctor_name: str) -> dict[str, Any]:
    """Apply doctor-specific style to a report template."""
    style = _STYLE_MAP.get(doctor_name, {})
    tone = style.get("tone", "concise_clinical")
    report = dict(template)

    # Vary language based on tone
    if tone == "urgent_direct":
        report["findings"] = report["findings"].replace("is present", "is identified — clinically significant")
        report["impressions"] = report["impressions"].upper() if random.random() < 0.2 else report["impressions"]
    elif tone == "structured_bullet":
        lines = report["findings"].split(". ")
        report["findings"] = "\n".join(f"- {l.strip().rstrip('.')}." for l in lines if l.strip())
    elif tone == "quantitative_precise":
        report["findings"] = report["findings"].replace("normal", "within expected physiologic range")
    elif tone == "longitudinal_comparative":
        report["findings"] = "Compared to prior study: " + report["findings"]
        report["impressions"] += "\n\nOverall assessment: Stable disease."

    return report


@router.post("/seed", status_code=201)
async def seed_demo_data() -> dict[str, Any]:
    """Seed 10 sample doctors with ~10 reports each for demo purposes.

    This endpoint does NOT require authentication so the demo can be
    initialised from any HTTP client.
    """
    # Ensure Cosmos DB is initialized (may not be if lifespan is skipped)
    if not cosmos_service._containers:
        await cosmos_service.initialize()

    created_doctors: list[dict[str, Any]] = []
    total_reports = 0

    for doc_info in SEED_DOCTORS:
        doctor = await cosmos_service.create_doctor(doc_info)
        created_doctors.append(doctor)

        # Seed style profile
        style_data = _STYLE_MAP.get(doc_info["name"], {})
        await cosmos_service.upsert_style_profile({
            "doctor_id": doctor["id"],
            "vocabulary_patterns": style_data.get("sample_phrases", []),
            "abbreviation_map": style_data.get("abbreviation_map", {}),
            "sentence_structure": [style_data.get("tone", "concise_clinical")],
            "section_ordering": ["findings", "impressions", "recommendations"],
            "sample_phrases": style_data.get("sample_phrases", []),
        })

        # Generate 10 reports per doctor using templates
        for i, template in enumerate(_REPORT_TEMPLATES):
            styled = _apply_doctor_style(template, doc_info["name"])
            days_ago = random.randint(1, 90)
            created_at = (datetime.utcnow() - timedelta(days=days_ago)).isoformat()
            statuses = ["draft", "draft", "edited", "final", "final"]

            grounding_conf = round(random.uniform(0.82, 0.99), 2)
            review_quality = round(random.uniform(0.78, 0.98), 2)

            report_data = {
                "id": str(uuid.uuid4()),
                "doctor_id": doctor["id"],
                "input_text": styled["input_text"],
                "report_type": styled["report_type"],
                "body_region": styled["body_region"],
                "findings": styled["findings"],
                "impressions": styled["impressions"],
                "recommendations": styled["recommendations"],
                "status": random.choice(statuses),
                "versions": [],
                "grounding": {
                    "is_grounded": True,
                    "overall_confidence": grounding_conf,
                    "section_scores": {
                        "findings": round(grounding_conf + random.uniform(-0.03, 0.01), 2),
                        "impressions": round(grounding_conf + random.uniform(-0.05, 0.02), 2),
                        "recommendations": round(min(1.0, grounding_conf + random.uniform(0, 0.05)), 2),
                    },
                    "issues": [],
                    "hallucinated_claims": [],
                },
                "review": {
                    "overall_quality": review_quality,
                    "medical_accuracy": round(review_quality + random.uniform(-0.02, 0.02), 2),
                    "terminology_correctness": round(min(1.0, review_quality + random.uniform(0, 0.05)), 2),
                    "completeness": round(review_quality + random.uniform(-0.05, 0.03), 2),
                    "style_adherence": round(review_quality + random.uniform(-0.08, 0.02), 2),
                    "critical_issues": [],
                    "suggestions": [],
                },
                "revisions": random.choice([0, 0, 0, 1, 1, 2]),
                "decision": "accepted",
                "pipeline_trace": [
                    {"agent": "style_analyst", "success": True, "confidence": round(random.uniform(0.88, 0.99), 2)},
                    {"agent": "clinical_rag", "success": True, "confidence": round(random.uniform(0.75, 0.95), 2)},
                    {"agent": "report_writer", "success": True, "confidence": round(random.uniform(0.85, 0.98), 2)},
                    {"agent": "grounding_validator", "success": True, "confidence": grounding_conf},
                    {"agent": "clinical_reviewer", "success": True, "confidence": review_quality},
                ],
                "created_at": created_at,
                "updated_at": created_at,
            }
            cosmos_service._container("reports").create_item(body=report_data)
            total_reports += 1

    logger.info("Seeded %d doctors and %d reports", len(created_doctors), total_reports)
    return {
        "message": f"Seeded {len(created_doctors)} doctors with {total_reports} reports",
        "doctors": [{"id": d["id"], "name": d["name"]} for d in created_doctors],
    }
