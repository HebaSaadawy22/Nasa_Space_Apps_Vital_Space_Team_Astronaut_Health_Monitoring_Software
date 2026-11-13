"""Shared constants: reference ranges, indicators, body systems, hazards and routine tasks.

Reference ranges are general adult values used for demonstration only.
They are not medical advice. See docs/scientific_references.md.
"""

LEVEL_NAMES = {0: "Normal", 1: "Watch", 2: "Alert"}
LEVEL_COLORS = {0: "#2fb26b", 1: "#e09a1f", 2: "#e5534b"}

MOODS = {5: "Very good", 4: "Good", 3: "Neutral", 2: "Low", 1: "Very low"}

# ok = normal range, warn = watch range, outside warn = alert
FIELDS = {
    "hr": {"label": "Heart rate", "unit": "bpm", "ok": (50, 90), "warn": (40, 110), "dec": 0, "step": 1, "min": 20, "max": 220},
    "sys": {"label": "Systolic", "unit": "mmHg", "ok": (90, 129), "warn": (80, 139), "dec": 0, "step": 1, "min": 60, "max": 240},
    "dia": {"label": "Diastolic", "unit": "mmHg", "ok": (60, 84), "warn": (50, 89), "dec": 0, "step": 1, "min": 30, "max": 150},
    "glucose": {"label": "Fasting glucose", "unit": "mg/dL", "ok": (70, 99), "warn": (60, 125), "dec": 0, "step": 1, "min": 30, "max": 500},
    "temp": {"label": "Temperature", "unit": "°C", "ok": (36.1, 37.2), "warn": (35.5, 37.9), "dec": 1, "step": 0.1, "min": 33, "max": 42},
    "sleep": {"label": "Sleep", "unit": "h", "ok": (7, 10), "warn": (5.5, 12), "dec": 1, "step": 0.1, "min": 0, "max": 16},
    "mood": {"label": "Mood", "unit": "/ 5", "ok": (4, 5), "warn": (3, 5), "dec": 0, "step": 1, "min": 1, "max": 5},
    "spo2": {"label": "Oxygen saturation", "unit": "%", "ok": (95, 100), "warn": (92, 100), "dec": 0, "step": 1, "min": 70, "max": 100},
    "exercise": {"label": "Exercise", "unit": "min", "ok": (90, 400), "warn": (45, 400), "dec": 0, "step": 5, "min": 0, "max": 600},
}
ORDER = ["hr", "sys", "dia", "glucose", "temp", "sleep", "mood", "spo2", "exercise"]

INDICATORS = [
    {"id": "hr", "name": "Heart rate", "fields": ["hr"], "system": "heart", "unit": "bpm",
     "how": "Sit still for 5 minutes. Use the wrist sensor, or count the pulse at your wrist for 30 seconds and double it.",
     "why": "Fluid shifts in microgravity and lost cardiovascular fitness change resting heart rate. Stress and fatigue can raise it.",
     "amber": ["Rest 10 minutes, then measure again", "Drink water and cut caffeine", "Note dizziness, chest tightness or palpitations"],
     "red": ["Stop strenuous work and rest", "Repeat with the second sensor", "Report the value and symptoms to the flight surgeon"]},
    {"id": "bp", "name": "Blood pressure", "fields": ["sys", "dia"], "system": "heart", "unit": "mmHg",
     "how": "Sit with the cuff at heart level and the arm relaxed. Take two readings one minute apart and log the second.",
     "why": "Fluid moves toward the head in microgravity, and pressure often drops on standing after return. Salty food and stress can push it up.",
     "amber": ["Measure again after 10 minutes of rest", "Review salt intake and hydration", "Keep logging twice a day for 3 days"],
     "red": ["Stop exercise and rest", "Repeat on the other arm", "Report to the flight surgeon, especially with headache, vision change or chest pain"]},
    {"id": "glucose", "name": "Glucose", "fields": ["glucose"], "system": "metabolism", "unit": "mg/dL",
     "how": "Use the fingerstick meter in the morning after at least 8 hours without food. Wash and dry the finger first.",
     "why": "Stress, poor sleep, less activity and limited food variety can all shift blood sugar on long missions.",
     "amber": ["Repeat after a confirmed 8 hour fast", "Review food choices and meal timing", "Add a short walk or cycle session"],
     "red": ["Repeat with a fresh test strip", "Report to the flight surgeon, especially with thirst, nausea or confusion", "Do not skip meals until you have guidance"]},
    {"id": "temp", "name": "Temperature", "fields": ["temp"], "system": "immune", "unit": "°C",
     "how": "Use the forehead or ear thermometer away from vents, after 15 minutes of rest.",
     "why": "Spaceflight changes immune function, and a shared closed cabin spreads infections quickly. A small rise is worth tracking early.",
     "amber": ["Re-measure after 15 minutes of rest", "Wipe shared surfaces and wash hands", "Watch for cough, sore throat or aches"],
     "red": ["Limit contact with crewmates where possible", "Wear a mask in shared areas", "Report to the flight surgeon with a symptom list"]},
    {"id": "sleep", "name": "Sleep", "fields": ["sleep"], "system": "brain", "unit": "h",
     "how": "Read last night from the wearable, or note bed and wake times in the sleep diary.",
     "why": "Light cycles, noise and workload cut sleep in orbit. Short sleep lowers mood, judgement and reaction time.",
     "amber": ["Hold a fixed sleep window tonight", "Dim lights and skip screens for 30 minutes before bed", "Use ear plugs and an eye mask"],
     "red": ["Tell the commander and reduce safety-critical tasks", "Ask the flight surgeon about sleep support", "Protect a full sleep period before the next critical task"]},
    {"id": "mood", "name": "Mood", "fields": ["mood"], "system": "brain", "unit": "/ 5",
     "how": "Rate how you felt today from 1 (very low) to 5 (very good). Trends matter more than a single day.",
     "why": "Isolation, confinement and distance from Earth affect behavioral health, and low mood often shows up before other signs.",
     "amber": ["Call family or a friend", "Take 15 minutes of personal time", "Tell a crewmate how you feel"],
     "red": ["Contact the behavioral health support team", "Talk to a crewmate you trust", "Do not carry it alone"]},
    {"id": "spo2", "name": "Oxygen saturation", "fields": ["spo2"], "system": "lungs", "unit": "%",
     "how": "Use the fingertip pulse oximeter with warm hands, sitting still for 30 seconds.",
     "why": "Cabin air depends on life support. High CO2 or poor airflow can cause headache and lower oxygen saturation.",
     "amber": ["Breathe slowly and measure again with warm hands", "Check cabin CO2 and airflow near your sleep station", "Note any headache"],
     "red": ["Check the cabin CO2 and oxygen readouts now", "Move to a well ventilated module", "Report to the flight surgeon immediately"]},
    {"id": "exercise", "name": "Exercise", "fields": ["exercise"], "system": "bones", "unit": "min",
     "how": "Add up resistance and aerobic minutes from the exercise device log.",
     "why": "Without gravity loading, bone and muscle are lost. Crews train about two hours a day to slow that.",
     "amber": ["Add a resistance session today", "Book exercise time in tomorrow's timeline", "Check that the exercise device works"],
     "red": ["Report an equipment or schedule block to mission control", "Do bodyweight or resistance band work", "Flag bone and muscle loss risk to the flight surgeon"]},
]
INDICATOR_BY_ID = {i["id"]: i for i in INDICATORS}

# x, y are positions on a 0..100 x 0..200 body map used by the interactive body page
SYSTEMS = {
    "brain": {"name": "Brain and mind", "x": 50, "y": 178,
              "function": "Controls sleep, mood, attention and decision making.",
              "spaceflight": "Isolation, confinement, disrupted light cycles and workload strain sleep and mood. Radiation may also affect the nervous system on long missions.",
              "countermeasure": "Keep a fixed sleep window, use scheduled lighting, talk with family and crew, and log mood daily."},
    "immune": {"name": "Immune system", "x": 38, "y": 150,
               "function": "Defends against infection and keeps dormant viruses in check.",
               "spaceflight": "Spaceflight stress, radiation and a shared closed cabin change immune function and can reactivate latent viruses.",
               "countermeasure": "Track temperature, keep surfaces clean, protect sleep and nutrition, and report fever early."},
    "lungs": {"name": "Lungs", "x": 44, "y": 136,
              "function": "Bring oxygen in and carry carbon dioxide out.",
              "spaceflight": "Cabin air depends on life support. Raised CO2 or dust can cause headache and low oxygen saturation.",
              "countermeasure": "Check CO2 readouts, keep filters clean, and report headaches that come with low readings."},
    "heart": {"name": "Heart and vessels", "x": 58, "y": 130,
              "function": "Pumps blood and regulates blood pressure.",
              "spaceflight": "The heart works less against gravity and fluid moves toward the head. Fitness drops without aerobic exercise.",
              "countermeasure": "Do daily aerobic exercise, stay hydrated, and follow the fluid protocol before landing."},
    "metabolism": {"name": "Metabolism", "x": 50, "y": 108,
                   "function": "Turns food into energy and keeps blood sugar stable.",
                   "spaceflight": "Stress, limited food variety and lower activity can shift glucose and body weight.",
                   "countermeasure": "Follow the menu plan, eat at regular times, and log fasting glucose."},
    "bones": {"name": "Bones and muscle", "x": 44, "y": 50,
              "function": "Support the body and produce movement.",
              "spaceflight": "With no gravity loading, bone density and muscle mass fall unless countermeasures are used.",
              "countermeasure": "Train with resistance and aerobic exercise about two hours a day and keep calcium and vitamin D on plan."},
}

ENVIRONMENTS = {
    "iss": {"name": "Space station", "delay": "Near real-time contact",
            "escalation": "Request a private medical conference with the flight surgeon now. Voice contact is available on most passes."},
    "moon": {"name": "Lunar base", "delay": "About 1.3 s one-way delay",
             "escalation": "Call the flight surgeon now. The delay is about 1.3 seconds each way, so a live conversation works."},
    "mars": {"name": "Mars transit", "delay": "3 to 22 min one-way delay",
             "escalation": "Send a written report to the flight surgeon now and follow the on-board protocol while you wait. A reply can take up to 44 minutes."},
}

HAZARDS = [
    {"id": "radiation", "name": "Space radiation", "text": "Raises long-term cancer, nervous system and immune risk.",
     "action": "Read your dosimeter and shelter during solar events.", "indicators": ["temp", "mood"]},
    {"id": "isolation", "name": "Isolation and confinement", "text": "Strains sleep, mood and crew relations.",
     "action": "Keep routines, contact home and check in with the crew.", "indicators": ["mood", "sleep"]},
    {"id": "distance", "name": "Distance from Earth", "text": "Delays help, so you decide first and report after.",
     "action": "Use the guidance here and send clear reports early.", "indicators": ["hr", "bp", "glucose"]},
    {"id": "gravity", "name": "Gravity fields", "text": "Weightlessness weakens bone, muscle and the heart.",
     "action": "Exercise daily and track pressure and heart rate.", "indicators": ["exercise", "hr", "bp"]},
    {"id": "closed", "name": "Hostile closed environment", "text": "Air, water, noise and microbes all depend on the vehicle.",
     "action": "Watch CO2, ventilation and infection signs.", "indicators": ["spo2", "temp"]},
]

TASKS = [
    {"id": "log", "label": "Log today's readings", "points": 10},
    {"id": "ex1", "label": "Morning exercise session", "points": 20},
    {"id": "ex2", "label": "Evening exercise session", "points": 20},
    {"id": "hyd", "label": "Finish the planned fluid ration", "points": 10},
    {"id": "dose", "label": "Read your personal radiation dosimeter", "points": 15},
    {"id": "call", "label": "Crew check-in or call home", "points": 15},
    {"id": "wind", "label": "Start wind-down 30 minutes before sleep", "points": 10},
]
