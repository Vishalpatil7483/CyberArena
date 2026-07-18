"""Seed sample labs.

Idempotent: labs are matched by slug, so re-running never duplicates.

Usage:
    python -m app.services.seed
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.lab import Lab, LabDifficulty

SAMPLE_LABS: list[dict] = [
    {
        "title": "SQL Injection Basics",
        "slug": "sql-injection-basics",
        "category": "Web Security",
        "difficulty": LabDifficulty.EASY,
        "estimated_time_minutes": 30,
        "points": 100,
        "description": (
            "Learn how unsanitized input reaches database queries and how "
            "attackers exploit it. Practice identifying injectable parameters "
            "in a deliberately vulnerable web app, then fix the flaw using "
            "parameterized queries."
        ),
    },
    {
        "title": "Cross-Site Scripting (XSS) Playground",
        "slug": "xss-playground",
        "category": "Web Security",
        "difficulty": LabDifficulty.EASY,
        "estimated_time_minutes": 45,
        "points": 100,
        "description": (
            "Explore reflected, stored, and DOM-based XSS in a sandboxed "
            "application. Understand how untrusted data ends up in the DOM "
            "and how output encoding and Content Security Policy stop it."
        ),
    },
    {
        "title": "Broken Authentication Deep Dive",
        "slug": "broken-authentication-deep-dive",
        "category": "Web Security",
        "difficulty": LabDifficulty.MEDIUM,
        "estimated_time_minutes": 60,
        "points": 200,
        "description": (
            "Investigate common authentication failures: weak session "
            "tokens, credential stuffing, and insecure password reset "
            "flows. Harden a sample application step by step."
        ),
    },
    {
        "title": "Packet Analysis with Wireshark",
        "slug": "packet-analysis-wireshark",
        "category": "Network Security",
        "difficulty": LabDifficulty.EASY,
        "estimated_time_minutes": 40,
        "points": 100,
        "description": (
            "Capture and dissect network traffic. Follow TCP streams, "
            "identify protocols, and extract credentials from unencrypted "
            "traffic to understand why TLS matters."
        ),
    },
    {
        "title": "Firewall Rules & Segmentation",
        "slug": "firewall-rules-segmentation",
        "category": "Network Security",
        "difficulty": LabDifficulty.MEDIUM,
        "estimated_time_minutes": 55,
        "points": 200,
        "description": (
            "Design layered firewall rules for a small business network. "
            "Segment servers, workstations, and guest Wi-Fi, then verify "
            "the policy by simulating traffic between zones."
        ),
    },
    {
        "title": "Man-in-the-Middle Attack Anatomy",
        "slug": "mitm-attack-anatomy",
        "category": "Network Security",
        "difficulty": LabDifficulty.HARD,
        "estimated_time_minutes": 90,
        "points": 300,
        "description": (
            "Study how ARP spoofing and rogue access points intercept "
            "traffic in a simulated network. Detect the attack from packet "
            "captures and deploy mitigations like dynamic ARP inspection."
        ),
    },
    {
        "title": "Classical Ciphers Workshop",
        "slug": "classical-ciphers-workshop",
        "category": "Cryptography",
        "difficulty": LabDifficulty.EASY,
        "estimated_time_minutes": 35,
        "points": 100,
        "description": (
            "Break Caesar, Vigenère, and substitution ciphers by hand and "
            "with frequency analysis. Understand why classical ciphers fail "
            "and what modern cryptography does differently."
        ),
    },
    {
        "title": "Hash Cracking & Password Storage",
        "slug": "hash-cracking-password-storage",
        "category": "Cryptography",
        "difficulty": LabDifficulty.MEDIUM,
        "estimated_time_minutes": 60,
        "points": 200,
        "description": (
            "Compare MD5, SHA-256, and bcrypt against dictionary and brute "
            "force attacks in a controlled environment. Learn why salting "
            "and slow hashes protect stored credentials."
        ),
    },
    {
        "title": "Linux Permissions & Privilege Escalation",
        "slug": "linux-permissions-privesc",
        "category": "Linux",
        "difficulty": LabDifficulty.MEDIUM,
        "estimated_time_minutes": 70,
        "points": 200,
        "description": (
            "Audit a misconfigured Linux host: world-writable files, SUID "
            "binaries, and overly permissive sudo rules. Escalate to root "
            "in a sandbox, then remediate every finding."
        ),
    },
    {
        "title": "Bash for Security Analysts",
        "slug": "bash-for-security-analysts",
        "category": "Linux",
        "difficulty": LabDifficulty.EASY,
        "estimated_time_minutes": 40,
        "points": 100,
        "description": (
            "Use grep, awk, find, and pipes to triage logs and hunt "
            "suspicious files. Build a small toolkit of one-liners every "
            "analyst should know."
        ),
    },
    {
        "title": "Disk Image Forensics",
        "slug": "disk-image-forensics",
        "category": "Digital Forensics",
        "difficulty": LabDifficulty.HARD,
        "estimated_time_minutes": 100,
        "points": 300,
        "description": (
            "Analyze a captured disk image: recover deleted files, build a "
            "timeline from filesystem metadata, and document findings in a "
            "defensible chain-of-custody report."
        ),
    },
    {
        "title": "Memory Forensics First Steps",
        "slug": "memory-forensics-first-steps",
        "category": "Digital Forensics",
        "difficulty": LabDifficulty.MEDIUM,
        "estimated_time_minutes": 75,
        "points": 200,
        "description": (
            "Examine a memory dump from a compromised workstation. Identify "
            "running processes, network connections, and injected code "
            "using volatility-style analysis techniques."
        ),
    },
    {
        "title": "Intro to Binary Reverse Engineering",
        "slug": "intro-binary-reverse-engineering",
        "category": "Reverse Engineering",
        "difficulty": LabDifficulty.HARD,
        "estimated_time_minutes": 120,
        "points": 300,
        "description": (
            "Disassemble a small crackme binary. Read x86-64 assembly, "
            "trace control flow, and recover the validation algorithm to "
            "produce a working key."
        ),
    },
    {
        "title": "Malware Behavior Analysis (Static)",
        "slug": "malware-behavior-analysis-static",
        "category": "Reverse Engineering",
        "difficulty": LabDifficulty.MEDIUM,
        "estimated_time_minutes": 80,
        "points": 200,
        "description": (
            "Safely examine the strings, imports, and structure of a "
            "defanged malware sample. Classify its likely capabilities "
            "without ever executing it."
        ),
    },
]


def seed_labs(db: Session) -> int:
    """Insert any sample labs that are not present yet. Returns count added."""
    existing_slugs = set(db.scalars(select(Lab.slug)))
    added = 0
    for data in SAMPLE_LABS:
        if data["slug"] in existing_slugs:
            continue
        db.add(Lab(**data))
        added += 1
    if added:
        db.commit()
    return added


def main() -> None:
    with SessionLocal() as db:
        added = seed_labs(db)
    print(f"Seeded {added} lab(s); {len(SAMPLE_LABS) - added} already present.")


if __name__ == "__main__":
    main()
