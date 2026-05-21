import numpy as np

ALL_SKILLS = [
    "ML", "Backend", "Frontend", "Design",
    "Cybersecurity", "Research", "Mobile", "DevOps"
]

ALL_DOMAINS = ["AI/ML", "Web/App Dev", "Cybersecurity", "Cloud/DevOps"]

EXPERIENCE_MAP = {"Beginner": 0.0, "Intermediate": 0.5, "Advanced": 1.0}

def build_vector(participant):
    skill_vec = [
        1 if s in (participant.get("skills") or []) else 0
        for s in ALL_SKILLS
    ]
    domain_vec = [
        1 if participant.get("domain") == d else 0
        for d in ALL_DOMAINS
    ]
    exp = EXPERIENCE_MAP.get(participant.get("experience_level"), 0.5)
    
    return np.array(skill_vec + domain_vec + [exp], dtype=float)


def compute_distance_matrix(participants):
    vectors = np.array([build_vector(p) for p in participants])
    
    # manual cosine distance to avoid sklearn dependency if needed
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1  # avoid division by zero
    normalized = vectors / norms
    similarity = normalized @ normalized.T
    distance = 1 - similarity
    
    return distance