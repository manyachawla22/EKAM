import uuid

def get_fake_participants(event_id: str) -> list:
    raw = [
        # AI/ML
        {"name": "Aarav Shah",      "institution": "IIT Delhi",      "skills": ["ML", "Research"],        "experience_level": "Advanced",      "domain": "AI/ML"},
        {"name": "Priya Nair",      "institution": "BITS Pilani",    "skills": ["ML", "Backend"],         "experience_level": "Intermediate",  "domain": "AI/ML"},
        {"name": "Rohan Mehta",     "institution": "NIT Trichy",     "skills": ["ML", "DevOps"],          "experience_level": "Beginner",      "domain": "AI/ML"},
        {"name": "Sneha Iyer",      "institution": "DTU",            "skills": ["Research", "ML"],        "experience_level": "Advanced",      "domain": "AI/ML"},
        {"name": "Kabir Joshi",     "institution": "VIT Vellore",    "skills": ["ML", "Mobile"],          "experience_level": "Intermediate",  "domain": "AI/ML"},
        {"name": "Ananya Rao",      "institution": "IIIT Hyderabad", "skills": ["Research", "Backend"],   "experience_level": "Advanced",      "domain": "AI/ML"},

        # Web/App Dev
        {"name": "Dev Patel",       "institution": "IIT Bombay",     "skills": ["Frontend", "Backend"],   "experience_level": "Advanced",      "domain": "Web/App Dev"},
        {"name": "Meera Krishnan",  "institution": "DTU",            "skills": ["Frontend", "Design"],    "experience_level": "Intermediate",  "domain": "Web/App Dev"},
        {"name": "Arjun Sharma",    "institution": "NIT Surathkal",  "skills": ["Backend", "DevOps"],     "experience_level": "Advanced",      "domain": "Web/App Dev"},
        {"name": "Tanya Gupta",     "institution": "Jadavpur",       "skills": ["Frontend", "Mobile"],    "experience_level": "Beginner",      "domain": "Web/App Dev"},
        {"name": "Vikram Singh",    "institution": "IIT Madras",     "skills": ["Backend", "ML"],         "experience_level": "Intermediate",  "domain": "Web/App Dev"},
        {"name": "Ishaan Bose",     "institution": "BITS Goa",       "skills": ["DevOps", "Backend"],     "experience_level": "Advanced",      "domain": "Web/App Dev"},

        # Cybersecurity
        {"name": "Riya Agarwal",    "institution": "SRCC",           "skills": ["Cybersecurity", "Research"],  "experience_level": "Advanced",     "domain": "Cybersecurity"},
        {"name": "Samir Chopra",    "institution": "IIT Kanpur",     "skills": ["Cybersecurity", "Backend"],   "experience_level": "Intermediate", "domain": "Cybersecurity"},
        {"name": "Diya Malhotra",   "institution": "Hindu College",  "skills": ["Cybersecurity", "ML"],        "experience_level": "Beginner",     "domain": "Cybersecurity"},
        {"name": "Rahul Verma",     "institution": "IIT Kharagpur",  "skills": ["Cybersecurity", "DevOps"],    "experience_level": "Advanced",     "domain": "Cybersecurity"},
        {"name": "Pooja Menon",     "institution": "Symbiosis",      "skills": ["Cybersecurity", "Frontend"],  "experience_level": "Intermediate", "domain": "Cybersecurity"},
        {"name": "Aditya Kumar",    "institution": "NMIMS",          "skills": ["Research", "Cybersecurity"],  "experience_level": "Beginner",     "domain": "Cybersecurity"},

        # Cloud/DevOps
        {"name": "Kritika Seth",    "institution": "NID Ahmedabad",  "skills": ["DevOps", "Backend"],     "experience_level": "Advanced",      "domain": "Cloud/DevOps"},
        {"name": "Manav Oberoi",    "institution": "IIT Guwahati",   "skills": ["DevOps", "Research"],    "experience_level": "Intermediate",  "domain": "Cloud/DevOps"},
        {"name": "Simran Kaur",     "institution": "PEC Chandigarh", "skills": ["DevOps", "Mobile"],      "experience_level": "Beginner",      "domain": "Cloud/DevOps"},
        {"name": "Nikhil Jain",     "institution": "IIT Roorkee",    "skills": ["DevOps", "ML"],          "experience_level": "Advanced",      "domain": "Cloud/DevOps"},
        {"name": "Ayesha Khan",     "institution": "Jamia Millia",   "skills": ["DevOps", "Design"],      "experience_level": "Intermediate",  "domain": "Cloud/DevOps"},
        {"name": "Harsh Tiwari",    "institution": "MNNIT Allahabad","skills": ["DevOps", "Cybersecurity"],"experience_level": "Beginner",      "domain": "Cloud/DevOps"},
    ]

    result = []
    for p in raw:
        p["id"] = str(uuid.uuid4())
        p["event_id"] = str(event_id)
        p["status"] = "confirmed"
        result.append(p)

    return result