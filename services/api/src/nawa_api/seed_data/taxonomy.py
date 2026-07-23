"""Shared vocabulary and content banks the seed script draws from.

Content is templated/combinatorial rather than hand-authored prose for every
one of the 220 applications — realism comes from varying persona, country,
sector, and technical domain across a bank of authentic-sounding fragments,
not from literary uniqueness. Ground-truth ids (hidden gems, dedup pairs) are
tracked by the caller, not here.
"""

SECTORS = [
    "health-tech",
    "water-tech",
    "agri-tech",
    "energy",
    "assistive-tech",
    "fintech",
    "edtech",
    "logistics",
]

SKILLS = [
    "mechanical-engineering",
    "electrical-engineering",
    "software-engineering",
    "biomedical-engineering",
    "chemical-engineering",
    "data-science",
    "ux-design",
    "business-development",
    "regulatory-affairs",
    "arabic-technical-writing",
    "manufacturing",
    "supply-chain",
]

GULF_COUNTRIES = ["QA", "SA", "AE", "KW", "OM", "BH"]
NORTH_AFRICA_COUNTRIES = ["EG", "TN", "MA", "DZ"]
LEVANT_COUNTRIES = ["JO", "LB"]
ALL_COUNTRIES = GULF_COUNTRIES + NORTH_AFRICA_COUNTRIES + LEVANT_COUNTRIES

PERSONAS = [
    ("graduate researcher", "باحث خريج"),
    ("hospital biomedical engineer", "مهندس طبي حيوي في مستشفى"),
    ("oil-and-gas technician", "فني في قطاع النفط والغاز"),
    ("agritech founder", "مؤسس شركة زراعية تقنية"),
    ("assistive-tech teacher", "معلم مهتم بالتقنية المساعدة"),
    ("mechanical engineering student", "طالب هندسة ميكانيكية"),
    ("public-health nurse", "ممرضة صحة عامة"),
    ("renewable-energy technician", "فني طاقة متجددة"),
]

TECH_DOMAINS_EN = [
    ("desalination membrane fouling detection", "water-tech"),
    ("sickle-cell point-of-care diagnostics", "health-tech"),
    ("date-palm red weevil pest detection", "agri-tech"),
    ("PV-panel dust mitigation coating", "energy"),
    ("low-cost prosthetic hand control", "assistive-tech"),
    ("Arabic sign-language recognition tutor", "assistive-tech"),
    ("smart irrigation for greenhouse farming", "agri-tech"),
    ("early wildfire smoke detection network", "energy"),
    ("microfinance credit-scoring for informal traders", "fintech"),
    ("Arabic dyslexia reading-assessment app", "edtech"),
]

TECH_DOMAINS_AR = [
    ("كشف تكلس أغشية تحلية المياه", "water-tech"),
    ("تشخيص فقر الدم المنجلي عند نقطة الرعاية", "health-tech"),
    ("كشف سوسة النخيل الحمراء في أشجار النخيل", "agri-tech"),
    ("طلاء لتخفيف تراكم الغبار على الألواح الشمسية", "energy"),
    ("طرف صناعي منخفض التكلفة للتحكم باليد", "assistive-tech"),
    ("تطبيق تعليمي للغة الإشارة العربية", "assistive-tech"),
    ("ري ذكي للزراعة المحمية", "agri-tech"),
    ("شبكة كشف مبكر لدخان حرائق الغابات", "energy"),
    ("تقييم ائتماني للتجار غير الرسميين", "fintech"),
    ("تطبيق لتقييم عسر القراءة باللغة العربية", "edtech"),
]

# Hidden-gem writing style: short, colloquial, occasionally typo-ridden — the
# signal the Intake Copilot exists to save, per the concept pack's brief.
HIDDEN_GEM_EN_TEMPLATES = [
    "so basicaly i made a thing that check the {domain} problem we have here, "
    "it work good in my village test, need help to make it bigger scale",
    "my idea is about {domain}. i tested with my cusin farm, save alot time. "
    "sorry my english not so good but the idea real and work",
    "we build small device for {domain} cheap, use in our clinic already, "
    "doctor say very useful, i need money and mentor to continue",
]

HIDDEN_GEM_AR_TEMPLATES = [
    "بصراحة الفكرة بسيطة، سويت جهاز صغير يحل مشكلة {domain} عندنا بالقرية "
    "واشتغل زين بس ما عندي فلوس اكمل، ياليت حد يساعدني",
    "انا موب متعلم كتير بس جربت شي يخص {domain} على مزرعة عمي ونجح، احتاج مساعدة اطور الفكرة اكثر",
]

STANDARD_EN_TEMPLATE = (
    "Our team has been working on {domain} for the past year. We have built "
    "a working prototype and tested it with {persona} contacts in {country}. "
    "The market need is significant: existing solutions are either imported, "
    "expensive, or not adapted to local conditions. We are seeking support to "
    "validate the technology at scale and reach paying customers across the "
    "region."
)

STANDARD_AR_TEMPLATE = (
    "يعمل فريقنا منذ عام على مشروع في مجال {domain}. قمنا ببناء نموذج أولي "
    "عامل واختبرناه مع جهات اتصال من فئة {persona} في {country}. الحاجة "
    "السوقية كبيرة، فالحلول الحالية إما مستوردة أو مكلفة أو غير ملائمة للظروف "
    "المحلية. نسعى للحصول على الدعم للتحقق من صحة التقنية على نطاق واسع "
    "والوصول إلى عملاء يدفعون في المنطقة."
)

FR_TEMPLATE = (
    "Notre équipe travaille depuis un an sur {domain}. Nous avons développé "
    "un prototype fonctionnel et l'avons testé avec des contacts de type "
    "{persona} au {country}. Le besoin du marché est important : les "
    "solutions existantes sont soit importées, soit coûteuses, soit mal "
    "adaptées aux conditions locales."
)

RESOURCE_TOPICS = [
    ("Program Program Handbook", "دليل برامج مركز قطر لعلوم وتكنولوجيا"),
    ("Fab Lab Capabilities", "قدرات مختبر التصنيع"),
    ("Chemistry Lab Safety Guide", "دليل سلامة مختبر الكيمياء"),
    ("Rapid Prototyping Services", "خدمات النمذجة السريعة"),
    ("Mentor Directory: Hardware", "دليل الموجهين: الأجهزة"),
    ("Mentor Directory: Biotech", "دليل الموجهين: التقنية الحيوية"),
    ("Frequently Asked Questions", "الأسئلة الشائعة"),
    ("IP and Patent Policy", "سياسة الملكية الفكرية وبراءات الاختراع"),
    ("Funding and Grants Guide", "دليل التمويل والمنح"),
    ("Regulatory Pathways in Qatar", "المسارات التنظيمية في قطر"),
]
