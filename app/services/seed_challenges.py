"""Sample challenge content for the seed script.

Challenges are keyed by lab slug. The "flag" key holds the plaintext
sample answer; app.services.seed hashes it at insert time — plaintext
flags are never stored in the database.
"""

from app.models.challenge import ChallengeType

SAMPLE_CHALLENGES: dict[str, list[dict]] = {
    "sql-injection-basics": [
        {
            "title": "Find the hidden admin page",
            "description": (
                "The vulnerable shop application has an admin panel that is "
                "not linked anywhere. Common paths and robots.txt are good "
                "places to look.\n\nSubmit the flag you find on the admin page."
            ),
            "challenge_type": ChallengeType.FLAG,
            "points": 50,
            "order_index": 1,
            "hint": "Check /robots.txt — what is being hidden from crawlers?",
            "flag": "CTF{robots_txt_is_not_security}",
        },
        {
            "title": "Comment archaeology",
            "description": (
                "Developers sometimes leave notes in HTML comments. Inspect "
                "the login page source of the demo shop and submit the flag "
                "left behind by a careless developer."
            ),
            "challenge_type": ChallengeType.FLAG,
            "points": 50,
            "order_index": 2,
            "hint": "View source (Ctrl+U) and search for <!--",
            "flag": "CTF{comments_are_public}",
        },
        {
            "title": "Decode the session token",
            "description": (
                "The demo shop stores a session token that looks like random "
                "text:\n\nQ1RGe2Jhc2U2NF9pc19ub3RfZW5jcnlwdGlvbn0=\n\n"
                "Decode it and submit the result."
            ),
            "challenge_type": ChallengeType.TEXT,
            "points": 100,
            "order_index": 3,
            "hint": "The trailing = is a strong hint that this is Base64.",
            "flag": "CTF{base64_is_not_encryption}",
        },
    ],
    "xss-playground": [
        {
            "title": "Reflected input",
            "description": (
                "The search box echoes your query straight into the page. "
                "What HTML element name would you inject to run script? "
                "Submit the element name in lowercase (no angle brackets)."
            ),
            "challenge_type": ChallengeType.QUIZ,
            "points": 50,
            "order_index": 1,
            "hint": "The classic XSS payload uses this tag.",
            "flag": "script",
        },
        {
            "title": "Cookie theft flag",
            "description": (
                "In the sandbox, a successful stored-XSS payload exfiltrates "
                "the admin cookie:\n\n"
                "admin_session=CTF{stored_xss_steals_sessions}\n\n"
                "Submit the flag portion."
            ),
            "challenge_type": ChallengeType.FLAG,
            "points": 100,
            "order_index": 2,
            "hint": "Submit only the CTF{...} value.",
            "flag": "CTF{stored_xss_steals_sessions}",
        },
    ],
    # --- Network Security ---
    "packet-analysis-wireshark": [
        {
            "title": 'Credentials on the wire',
            "description": 'A capture of an FTP session contains a cleartext login. The password is the flag.\n\nCapture excerpt:\n220 FTP ready\nUSER analyst\n331 Password required\nPASS CTF{ftp_sends_cleartext}\n230 Login successful',
            "challenge_type": ChallengeType.FLAG,
            "points": 75,
            "order_index": 1,
            "hint": 'Look at the PASS command.',
            "flag": 'CTF{ftp_sends_cleartext}',
        },
        {
            "title": 'Port of call',
            "description": 'In the same capture the client connects to the FTP control channel. Which TCP port is it? Submit the number.',
            "challenge_type": ChallengeType.QUIZ,
            "points": 25,
            "order_index": 2,
            "hint": 'It is the standard FTP control port.',
            "flag": '21',
        },
    ],
    # --- Cryptography ---
    "classical-ciphers-workshop": [
        {
            "title": 'Caesar salad',
            "description": 'Decrypt this Caesar-shifted message (shift 3):\n\nFWI{fdhvdu_lv_euxwh_irufhdeoh}\n\nSubmit the plaintext.',
            "challenge_type": ChallengeType.TEXT,
            "points": 50,
            "order_index": 1,
            "hint": 'Shift every letter back by 3 positions.',
            "flag": 'CTF{caesar_is_brute_forceable}',
        },
        {
            "title": 'ROT13 rotation',
            "description": 'This message was ROT13 encoded:\n\nPGS{ebg13_vf_abg_rapelcgvba}\n\nSubmit the plaintext.',
            "challenge_type": ChallengeType.TEXT,
            "points": 50,
            "order_index": 2,
            "hint": 'ROT13 is its own inverse — apply it again.',
            "flag": 'CTF{rot13_is_not_encryption}',
        },
        {
            "title": 'Single-byte XOR',
            "description": 'The text below was XORed with the single byte 0x20:\n\nctf{xor_needs_a_real_key}\n\nXOR it back and submit the result. (Notice what XOR with 0x20 does to letter case.)',
            "challenge_type": ChallengeType.TEXT,
            "points": 100,
            "order_index": 3,
            "hint": 'XOR with 0x20 flips the case of ASCII letters.',
            "flag": 'CTF{XOR_NEEDS_A_REAL_KEY}',
        },
    ],
    # --- Linux ---
    "linux-permissions-privesc": [
        {
            "title": 'Reading the mode bits',
            "description": 'A file lists as:\n\n-rwsr-xr-x 1 root root 68208 backup\n\nWhat is the four-digit octal mode of this file? Submit the number.',
            "challenge_type": ChallengeType.QUIZ,
            "points": 75,
            "order_index": 1,
            "hint": 'The s in the owner execute slot is the setuid bit (4).',
            "flag": '4755',
        },
        {
            "title": 'The dotfile drop',
            "description": 'An attacker stashed a flag in a hidden file in /home/analyst. You ran:\n\n$ cat /home/analyst/.secret_stash\nCTF{dotfiles_hide_in_plain_sight}\n\nSubmit the flag.',
            "challenge_type": ChallengeType.FLAG,
            "points": 50,
            "order_index": 2,
            "hint": 'Files starting with a dot need ls -a to appear.',
            "flag": 'CTF{dotfiles_hide_in_plain_sight}',
        },
    ],
    # --- Reverse Engineering ---
    "intro-binary-reverse-engineering": [
        {
            "title": 'Strings attached',
            "description": 'Running strings on the crackme binary reveals:\n\n/lib64/ld-linux-x86-64.so.2\nlibc.so.6\nEnter key:\nCTF{strings_finds_secrets}\nWrong key!\n\nSubmit the embedded flag.',
            "challenge_type": ChallengeType.FLAG,
            "points": 100,
            "order_index": 1,
            "hint": 'One of those strings is not like the others.',
            "flag": 'CTF{strings_finds_secrets}',
        },
    ],
    # --- Digital Forensics ---
    "disk-image-forensics": [
        {
            "title": 'Metadata never lies',
            "description": 'EXIF data extracted from a recovered photo includes:\n\nCamera: NX-500\nGPS: redacted\nComment: CTF{exif_reveals_everything}\n\nSubmit the flag hidden in the metadata.',
            "challenge_type": ChallengeType.FLAG,
            "points": 100,
            "order_index": 1,
            "hint": 'Check the Comment field.',
            "flag": 'CTF{exif_reveals_everything}',
        },
    ],
}
