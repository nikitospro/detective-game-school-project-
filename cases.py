from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from random import Random
from typing import Any


@dataclass(frozen=True)
class Suspect:
    suspect_id: str
    name: str
    role: str
    short_backstory: str
    personality_traits: list[str]
    speaking_style: str
    motive: str
    alibi: str
    hidden_secrets: list[str]
    known_facts: list[str]
    relationship_to_victim: str
    stress_level: int
    private_strategy: str
    pressure_points: list[str]


@dataclass(frozen=True)
class Clue:
    clue_id: str
    title: str
    description: str
    found_at: str
    interpretation: str
    related_suspects: list[str]
    misleading: bool
    critical: bool
    keywords: list[str]


@dataclass(frozen=True)
class Contradiction:
    contradiction_id: str
    title: str
    description: str
    suspect_ids: list[str]
    clue_ids: list[str]
    severity: int
    unlock_after_questions: int = 1


@dataclass(frozen=True)
class Solution:
    culprit_id: str
    culprit_name: str
    motive: str
    key_evidence: list[str]
    contradictions: list[str]
    logical_explanation: str
    motive_keywords: list[str]
    evidence_keywords: dict[str, list[str]]


@dataclass(frozen=True)
class CaseFile:
    case_id: str
    title: str
    introduction: str
    location: str
    timeline: list[str]
    victim_name: str
    difficulty_label: str
    summary_hint: str
    suspects: list[Suspect]
    clues: list[Clue]
    contradictions: list[Contradiction]
    solution: Solution
    origin: str = "local"
    generator_seed: int | None = None
    generator_theme: str | None = None
    generator_theme_label: str | None = None

    def suspect_by_id(self, suspect_id: str) -> Suspect:
        return next(suspect for suspect in self.suspects if suspect.suspect_id == suspect_id)

    def clue_by_id(self, clue_id: str) -> Clue:
        return next(clue for clue in self.clues if clue.clue_id == clue_id)

    @property
    def source_label(self) -> str:
        if self.origin == "generated":
            return "Сгенерировано"
        return "Локальное"


@dataclass(frozen=True)
class RoleProfile:
    key: str
    role: str
    backstory_templates: list[str]
    motive_templates: list[str]
    alibi_templates: list[str]
    secret_templates: list[str]
    fact_templates: list[str]
    relationship_templates: list[str]
    speaking_styles: list[str]
    strategy_templates: list[str]
    pressure_points: list[str]
    trait_sets: list[tuple[str, str, str]]


@dataclass(frozen=True)
class ProceduralTheme:
    key: str
    label: str
    pitch: str
    title_templates: list[str]
    venue_names: list[str]
    locations: list[str]
    events: list[str]
    victim_roles: list[str]
    restricted_areas: list[str]
    public_areas: list[str]
    side_areas: list[str]
    documents: list[str]
    traces: list[str]
    crime_objects: list[str]


FIRST_NAMES = [
    "Алина",
    "Виктор",
    "Вера",
    "Глеб",
    "Дина",
    "Егор",
    "Жанна",
    "Злата",
    "Илья",
    "Кира",
    "Лев",
    "Марина",
    "Ника",
    "Олег",
    "Павел",
    "Рита",
    "Светлана",
    "Тимур",
    "Ульяна",
    "Фёдор",
    "Юлия",
    "Ярослав",
]

LAST_NAMES = [
    "Андреева",
    "Белов",
    "Воронова",
    "Громов",
    "Доронина",
    "Ершов",
    "Жукова",
    "Зайцев",
    "Исаева",
    "Климов",
    "Ларионова",
    "Мартынов",
    "Назарова",
    "Орехов",
    "Панина",
    "Рыков",
    "Сафонова",
    "Третьяков",
    "Уварова",
    "Фомин",
    "Черкасова",
    "Шестаков",
]

ROLE_PROFILES = [
    RoleProfile(
        key="operations_manager",
        role="Операционный менеджер площадки",
        backstory_templates=[
            "Много лет держит объект в собранном состоянии и знает, где внутренние процедуры дают слабину.",
            "Привык(ла) закрывать организационные провалы до того, как о них узнаёт руководство.",
        ],
        motive_templates=[
            "Жертва собиралась сверить {document_name} и могла увидеть служебную несостыковку, которая ударила бы по репутации отдела.",
            "После спора о {crime_object} опасался(ась), что жертва устроит персональную проверку и снимет с должности.",
        ],
        alibi_templates=[
            "Утверждает, что с {time_service} до {time_photo} находился(лась) у {public_area}, координируя {event_name}.",
            "Говорит, что почти весь критический промежуток провёл(а) между {public_area} и {side_area}, решая организационный сбой.",
        ],
        secret_templates=[
            "Скрытно перенёс(ла) одну служебную папку из {restricted_area}, чтобы утром переписать неудобную строку.",
            "Просил(а) дежурную смену не отмечать короткий технический сбой, чтобы не сорвать вечер.",
        ],
        fact_templates=[
            "Его(её) пропуск регулярно открывал дверь в {restricted_area}.",
            "Именно этот человек последним подтверждал готовность зоны {public_area}.",
        ],
        relationship_templates=[
            "Работал(а) с жертвой почти ежедневно и часто спорил(а) с ней о дисциплине.",
            "Для жертвы был(а) незаменимым координатором, но в последние недели их разговоры становились жёстче.",
        ],
        speaking_styles=[
            "Говорит быстро и деловито, будто закрывает совещание.",
            "Отвечает сухо, старается свести разговор к регламенту и срокам.",
        ],
        strategy_templates=[
            "Уводить разговор в сторону процедур и не давать следователю превратить служебную ошибку в признание.",
            "Давить на загруженность вечера и делать вид, что хаос площадки всё объясняет сам по себе.",
        ],
        pressure_points=["регламент", "смена", "координация"],
        trait_sets=[("собранный", "жёсткий", "выносливый"), ("напряжённый", "деловой", "резкий")],
    ),
    RoleProfile(
        key="security_chief",
        role="Начальник охраны",
        backstory_templates=[
            "Следит за безопасностью объекта и знает, где камеры оставляют слепые зоны.",
            "Привык(ла) мыслить маршрутами, допусками и обходами, а не чужими эмоциями.",
        ],
        motive_templates=[
            "Жертва собиралась поднять вопрос о доступах в {restricted_area} и грозила внутренним разбирательством.",
            "После разговора о слепой зоне возле {side_area} понял(а), что к утру может лишиться поста.",
        ],
        alibi_templates=[
            "Говорит, что в момент инцидента проверял(а) обход между {side_area} и {public_area}.",
            "Утверждает, что контролировал(а) поток гостей у {public_area} и не отходил(а) к {restricted_area}.",
        ],
        secret_templates=[
            "Откладывал(а) доклад о коротком отключении камеры, чтобы не портить картину вечера.",
            "Разрешил(а) провести через служебный вход лишний контейнер без лишних записей.",
        ],
        fact_templates=[
            "У него(неё) есть права доступа к панели камер и журналу перемещений.",
            "Именно этот человек подписывал финальный отчёт по охране перед закрытием смены.",
        ],
        relationship_templates=[
            "С жертвой связывал только жёсткий рабочий контакт, в котором никто не уступал первым.",
            "Жертва доверяла безопасности объекта, но регулярно давила на него(неё) из-за каждой ошибки.",
        ],
        speaking_styles=[
            "Отвечает рублено, почти приказным тоном, не любит повторять очевидное.",
            "Говорит кратко и напряжённо, будто каждое слово потом уйдёт в протокол.",
        ],
        strategy_templates=[
            "Сужать разговор до маршрутов и не признавать, что система наблюдения могла быть использована вручную.",
            "Показывать уверенность и заставлять следователя сомневаться в интерпретации технических логов.",
        ],
        pressure_points=["камера", "доступ", "журнал"],
        trait_sets=[("сдержанный", "подозрительный", "жёсткий"), ("холодный", "практичный", "колкий")],
    ),
    RoleProfile(
        key="finance_coordinator",
        role="Финансовый координатор",
        backstory_templates=[
            "Следит за платежами и сметой так внимательно, что знает цену каждой ошибки.",
            "Привык(ла) держать документы в порядке, даже если ради этого приходится сглаживать неудобные детали.",
        ],
        motive_templates=[
            "Жертва начала сверять {document_name} и могла вскрыть денежную дыру, которую уже было нечем прикрыть.",
            "Паниковал(а), что после ревизии всплывёт подмена строки в {document_name}, а вместе с ней и личные долги.",
        ],
        alibi_templates=[
            "Заявляет, что почти всё критическое время провёл(а) у кассового терминала возле {public_area}.",
            "Уверяет, что до сигнала тревоги сидел(а) над {document_name} и не выходил(а) из зоны {side_area}.",
        ],
        secret_templates=[
            "Уже переписывал(а) одну строку в {document_name}, надеясь закрыть её утром как служебную правку.",
            "Спрятал(а) личный чек в папке с документами, чтобы никто не увидел связь с долгами.",
        ],
        fact_templates=[
            "Именно его(её) подпись стоит на последней версии {document_name}.",
            "Жертва в тот вечер просила этого человека остаться после закрытия для сверки цифр.",
        ],
        relationship_templates=[
            "Жертва считала его(её) полезным, но всё чаще проверяла лично, будто больше не доверяла отчётам.",
            "Рабочая связь с жертвой держалась на деньгах и взаимной нервозности.",
        ],
        speaking_styles=[
            "Говорит осторожно, будто каждое слово имеет цену и может стать лишней уликой.",
            "Отвечает тихо, но старается казаться рациональным и бесстрастным человеком.",
        ],
        strategy_templates=[
            "Признавать мелкие бухгалтерские грехи, но не подпускать следователя к главной дыре в документах.",
            "Делать вид, что вся история упирается в стресс и пересортицу бумаг, а не в умысел.",
        ],
        pressure_points=["смета", "ревизия", "долги"],
        trait_sets=[("расчётливый", "сдержанный", "уставший"), ("нервный", "точный", "осторожный")],
    ),
    RoleProfile(
        key="technical_specialist",
        role="Технический специалист",
        backstory_templates=[
            "Держит на себе аппаратуру и сервисные проходы, поэтому знает объект лучше большинства гостей.",
            "Привык(ла) решать проблемы до того, как о них успевают сказать вслух.",
        ],
        motive_templates=[
            "Жертва нашла связь между списанием узла {crime_object} и серией странных заявок на обслуживание.",
            "Опасался(ась), что после разговора о {restricted_area} всплывёт несанкционированный доступ к оборудованию.",
        ],
        alibi_templates=[
            "Утверждает, что всё время проверял(а) линию питания у {side_area} и не появлялся(ась) рядом с {restricted_area}.",
            "Говорит, что возился(ась) с аварийным щитом возле {side_area}, пока другие были заняты {event_name}.",
        ],
        secret_templates=[
            "Использовал(а) служебный ключ, чтобы без заявки попасть в {restricted_area}.",
            "Прятал(а) часть инструмента в закрытом шкафу, который не должен был открываться в эту смену.",
        ],
        fact_templates=[
            "Следы обслуживания вокруг {restricted_area} ведут к его(её) комплекту инструмента.",
            "Этот человек последним подтверждал готовность узла {crime_object} перед началом вечера.",
        ],
        relationship_templates=[
            "С жертвой связывали регулярные технические конфликты: один требовал идеальный результат, другой просил время.",
            "Жертва не считала технику мелочью и постоянно давила на него(неё) из-за рисков.",
        ],
        speaking_styles=[
            "Говорит предметно и резко, любит заменять эмоции техническими деталями.",
            "Отвечает коротко, иногда почти раздражённо, будто разговор мешает работе.",
        ],
        strategy_templates=[
            "Прятаться за сложность техники и вынуждать следователя путаться в терминах.",
            "Сводить всё к аварийному режиму и не обсуждать, кто именно им управлял вручную.",
        ],
        pressure_points=["щит", "инструмент", "сервис"],
        trait_sets=[("резкий", "собранный", "нервный"), ("практичный", "упрямый", "быстрый")],
    ),
    RoleProfile(
        key="program_curator",
        role="Куратор программы",
        backstory_templates=[
            "Отвечает за гостей, расписание и витрину события, поэтому постоянно балансирует между людьми и репутацией.",
            "Привык(ла) превращать хаос площадки в красивую картинку, даже если за кулисами всё трещит.",
        ],
        motive_templates=[
            "Жертва собиралась сорвать {event_name} и лично назвать виновного в провале вокруг {crime_object}.",
            "Боялся(ась), что после полуночи жертва расскажет партнёрам о несанкционированной договорённости вокруг {crime_object}.",
        ],
        alibi_templates=[
            "Говорит, что не отходил(а) от гостей в зоне {public_area}, потому что там держался весь вечерний ритм.",
            "Уверяет, что с начала конфликта находился(лась) между {public_area} и {side_area}, собирая расписание заново.",
        ],
        secret_templates=[
            "Пытался(ась) в частном порядке договориться с жертвой, чтобы та не поднимала скандал до конца вечера.",
            "Скрыл(а) одну рабочую переписку, которая показывает, насколько близко вечер был к срыву.",
        ],
        fact_templates=[
            "Именно этот человек первым просил у жертвы ещё один шанс сохранить вечер без скандала.",
            "Его(её) имя фигурирует в списке поздних переговоров с партнёрами события.",
        ],
        relationship_templates=[
            "С жертвой у него(неё) была смесь восхищения и раздражения: один делал лицо проекта, другой мог его уничтожить.",
            "Жертва считала его(её) полезным медиатором, пока не решила, что медиаобраз важнее правды.",
        ],
        speaking_styles=[
            "Говорит образно и уверенно, будто строит версию для прессы.",
            "Отвечает красиво, но слишком старается контролировать впечатление от каждого слова.",
        ],
        strategy_templates=[
            "Уводить разговор к атмосфере вечера и делать вид, что любая несостыковка родилась из общего хаоса.",
            "Признавать эмоциональный конфликт, но не подпускать следователя к закулисной сделке.",
        ],
        pressure_points=["гости", "пресса", "вечер"],
        trait_sets=[("харизматичный", "нервный", "быстрый"), ("собранный", "ироничный", "амбициозный")],
    ),
]

PROCEDURAL_THEMES = {
    "mountain_hotel": ProceduralTheme(
        key="mountain_hotel",
        label="Горный отель",
        pitch="Зимний комплекс, тревожная ночь, снег и закрытые сервисные переходы.",
        title_templates=[
            "Снег над {venue_name}",
            "Ночная смена отеля «{venue_name}»",
            "Тишина в комплексе «{venue_name}»",
        ],
        venue_names=["Перевал", "Северный гребень", "Айсбург", "Хрустальный склон"],
        locations=["Красная Поляна", "Шерегеш", "Архыз"],
        events=["ночным приёмом гостей", "приватным ужином инвесторов", "закрытой презентацией курорта"],
        victim_roles=["директор комплекса", "управляющий отелем", "руководитель ночной смены"],
        restricted_areas=["сервисный тоннель под корпусом", "технический коридор к котельной", "закрытый архив смены"],
        public_areas=["вестибюль главного корпуса", "панорамный бар", "зал приёма гостей"],
        side_areas=["зону служебных лифтов", "кладовую бельевого этажа", "диспетчерскую у кухни"],
        documents=["ночной отчёт загрузки", "черновик страхового акта", "служебную смету корпуса"],
        traces=["кварцевый снег", "пыль от противоскользящей смеси", "волокно утеплённой перчатки"],
        crime_objects=["сервисного щита", "страхового пакета", "дорогого инвентаря"],
    ),
    "science_lab": ProceduralTheme(
        key="science_lab",
        label="Исследовательская лаборатория",
        pitch="Закрытый научный блок, протоколы доступа и спор о дорогостоящем проекте.",
        title_templates=[
            "После полуночи в комплексе «{venue_name}»",
            "Последний протокол лаборатории «{venue_name}»",
            "Сбой в блоке «{venue_name}»",
        ],
        venue_names=["Кварц", "Градиент", "Нейрон", "Сигма-9"],
        locations=["Дубна", "Зеленоград", "Новосибирск"],
        events=["закрытой демонстрацией прототипа", "внутренней защитой проекта", "визитом инвесторов в лабораторию"],
        victim_roles=["научный руководитель", "координатор эксперимента", "директор исследовательского блока"],
        restricted_areas=["чистый модуль хранения", "лабораторный архив", "сервисный шлюз установки"],
        public_areas=["демонстрационный зал", "переговорную секцию", "центральный коридор блока"],
        side_areas=["серверную нишу", "комнату калибровки", "пост оператора"],
        documents=["протокол ревизии реактивов", "черновик грантового отчёта", "акта списания модуля"],
        traces=["флуоресцентная пыль", "следы лабораторного геля", "волокно антистатического рукава"],
        crime_objects=["лабораторного модуля", "прототипа установки", "контрольного образца"],
    ),
    "tv_studio": ProceduralTheme(
        key="tv_studio",
        label="Телестудия",
        pitch="Прямой эфир сорван, а закулисье оказывается куда опаснее камеры.",
        title_templates=[
            "Молчание после эфира «{venue_name}»",
            "Последний свет в студии «{venue_name}»",
            "Срыв смены на площадке «{venue_name}»",
        ],
        venue_names=["Полярис", "Кадр 12", "Сфера", "Ночной контур"],
        locations=["Москва", "Санкт-Петербург", "Казань"],
        events=["прямым эфиром рейтингового шоу", "ночной записью специального выпуска", "закрытой презентацией нового формата"],
        victim_roles=["исполнительный продюсер", "главный режиссёр смены", "директор студийного блока"],
        restricted_areas=["аппаратную резервного эфира", "архив монтажной", "служебный коридор за декорациями"],
        public_areas=["главную студию", "зону грима", "гостевой холл канала"],
        side_areas=["склад реквизита", "монтажную комнату", "диспетчерскую света"],
        documents=["производственный сметный лист", "черновик страхового отчёта по декорациям", "ведомость срочных выплат"],
        traces=["блестящую сценическую пыль", "волокно кабельной оплётки", "клейкую крошку со сцены"],
        crime_objects=["резервного передатчика", "дорогих декораций", "служебного реквизита"],
    ),
    "river_terminal": ProceduralTheme(
        key="river_terminal",
        label="Речной терминал",
        pitch="Поздняя смена у воды, путаница в накладных и служебный проход к причалу.",
        title_templates=[
            "Туман над терминалом «{venue_name}»",
            "Последний причал терминала «{venue_name}»",
            "Ночной груз в комплексе «{venue_name}»",
        ],
        venue_names=["Норд-Ривер", "Синий фарватер", "Гранитный причал", "Пятый рейд"],
        locations=["Нижний Новгород", "Самара", "Ростов-на-Дону"],
        events=["закрытой перегрузкой срочного груза", "ночной инспекцией терминала", "приёмом партнёров по контракту"],
        victim_roles=["начальник терминала", "координатор грузовой смены", "директор портового участка"],
        restricted_areas=["служебный тоннель к причалу", "доковый архив", "закрытый отсек контрольных пломб"],
        public_areas=["зал диспетчерской", "площадку перед причалом", "контрольный мостик"],
        side_areas=["склад таможенного досмотра", "узел резервного питания", "комнату дежурного механика"],
        documents=["черновик таможенного отчёта", "ночную ведомость рейса", "служебный акт пломбировки"],
        traces=["речную глину", "смазку с грузовой тележки", "волокно сигнального жилета"],
        crime_objects=["запасных пломб", "дорогого контейнера", "резервного терминального модуля"],
    ),
}


def _slug(text: str) -> str:
    cleaned = (
        text.lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("«", "")
        .replace("»", "")
        .replace("'", "")
    )
    cleaned = re.sub(r"[^a-zа-яё0-9_]+", "", cleaned)
    return cleaned.strip("_") or "custom"


def make_generated_case_id(theme_key: str, seed: int) -> str:
    return f"generated::{theme_key}::{seed}"


def parse_generated_case_id(case_id: str) -> tuple[str, int] | None:
    if not case_id.startswith("generated::"):
        return None
    _, theme_key, seed_text = case_id.split("::", 2)
    if theme_key not in PROCEDURAL_THEMES:
        return None
    try:
        return theme_key, int(seed_text)
    except ValueError:
        return None


def _safe_custom_text(value: Any, fallback: str, *, max_length: int = 90) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        cleaned = fallback
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:max_length].strip() or fallback


def _split_custom_list(
    value: Any,
    fallback: list[str],
    *,
    minimum: int = 4,
    maximum: int = 5,
) -> list[str]:
    if isinstance(value, list):
        raw_items = [str(item) for item in value]
    else:
        raw_items = re.split(r"[\n,;]+", str(value or ""))
    items = []
    for item in raw_items:
        cleaned = _safe_custom_text(item, "", max_length=60)
        if cleaned and cleaned not in items:
            items.append(cleaned)

    for item in fallback:
        if len(items) >= minimum:
            break
        if item not in items:
            items.append(item)

    return items[:maximum]


def normalize_custom_theme_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    raw = payload or {}
    venue_name = _safe_custom_text(raw.get("venue_name"), "Неоновый перекрёсток")
    theme_label = _safe_custom_text(raw.get("theme_label"), "Кастомная тема")
    case_title = _safe_custom_text(raw.get("case_title"), "", max_length=110)
    default_roles = [
        "Хозяин площадки",
        "Специалист по безопасности",
        "Финансовый посредник",
        "Технический эксперт",
        "Публичный куратор",
    ]
    suspect_roles = _split_custom_list(raw.get("suspect_roles"), default_roles)

    return {
        "theme_label": theme_label,
        "pitch": _safe_custom_text(
            raw.get("pitch"),
            f"Авторская тема вокруг объекта «{venue_name}», где каждый участник скрывает личный интерес.",
            max_length=180,
        ),
        "case_title": case_title,
        "venue_name": venue_name,
        "location": _safe_custom_text(raw.get("location"), "Авторская локация"),
        "event_name": _safe_custom_text(raw.get("event_name"), "закрытым вечерним событием"),
        "victim_role": _safe_custom_text(raw.get("victim_role"), "организатор события"),
        "restricted_area": _safe_custom_text(raw.get("restricted_area"), "закрытый служебный сектор"),
        "public_area": _safe_custom_text(raw.get("public_area"), "главная открытая зона"),
        "side_area": _safe_custom_text(raw.get("side_area"), "боковая техническая зона"),
        "document_name": _safe_custom_text(raw.get("document_name"), "спорный внутренний отчёт"),
        "trace_material": _safe_custom_text(raw.get("trace_material"), "редкая пыль с места"),
        "crime_object": _safe_custom_text(raw.get("crime_object"), "ценный предмет конфликта"),
        "suspect_roles": suspect_roles,
    }


def _custom_theme_fingerprint(payload: dict[str, Any]) -> str:
    normalized = normalize_custom_theme_payload(payload)
    packed = json.dumps(normalized, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(packed.encode("utf-8")).hexdigest()[:12]


def make_custom_case_id(payload: dict[str, Any], seed: int) -> str:
    return f"custom::{seed}::{_custom_theme_fingerprint(payload)}"


def parse_custom_case_id(case_id: str) -> tuple[int, str] | None:
    if not case_id.startswith("custom::"):
        return None
    try:
        _, seed_text, fingerprint = case_id.split("::", 2)
        return int(seed_text), fingerprint
    except ValueError:
        return None


def _full_name_pool() -> list[str]:
    return [f"{first} {last}" for first in FIRST_NAMES for last in LAST_NAMES]


def _pick_names(rng: Random, count: int) -> list[str]:
    return rng.sample(_full_name_pool(), count)


def _clamp(value: int, lower: int, upper: int) -> int:
    return max(lower, min(upper, value))


def _build_generated_suspects(
    *,
    rng: Random,
    victim_name: str,
    document_name: str,
    crime_object: str,
    restricted_area: str,
    public_area: str,
    side_area: str,
    event_name: str,
    names: list[str],
    culprit_index: int,
    red_herring_index: int,
    time_service: str,
    time_photo: str,
    role_profiles: list[RoleProfile],
) -> list[Suspect]:
    suspects: list[Suspect] = []
    victim_first = victim_name.split()[0]

    for index, profile in enumerate(role_profiles):
        trait_set = rng.choice(profile.trait_sets)
        stress = 44 + index * 4
        if index == culprit_index:
            stress += 24
        elif index == red_herring_index:
            stress += 12

        context = {
            "victim_first": victim_first,
            "victim_name": victim_name,
            "document_name": document_name,
            "crime_object": crime_object,
            "restricted_area": restricted_area,
            "public_area": public_area,
            "side_area": side_area,
            "event_name": event_name,
            "time_service": time_service,
            "time_photo": time_photo,
        }
        backstory = rng.choice(profile.backstory_templates).format(**context)
        motive = rng.choice(profile.motive_templates).format(**context)
        alibi = rng.choice(profile.alibi_templates).format(**context)
        secrets = [
            rng.choice(profile.secret_templates).format(**context),
            rng.choice(profile.secret_templates[::-1]).format(**context),
        ]
        facts = [
            rng.choice(profile.fact_templates).format(**context),
            rng.choice(profile.fact_templates[::-1]).format(**context),
        ]
        relationship = rng.choice(profile.relationship_templates).format(**context)
        strategy = rng.choice(profile.strategy_templates).format(**context)
        pressure_points = list(dict.fromkeys(profile.pressure_points + [_slug(document_name), _slug(restricted_area)]))[:4]

        suspects.append(
            Suspect(
                suspect_id=f"{profile.key}_{index}",
                name=names[index],
                role=profile.role,
                short_backstory=backstory,
                personality_traits=list(trait_set),
                speaking_style=rng.choice(profile.speaking_styles),
                motive=motive,
                alibi=alibi,
                hidden_secrets=secrets,
                known_facts=facts,
                relationship_to_victim=relationship,
                stress_level=_clamp(stress, 38, 89),
                private_strategy=strategy,
                pressure_points=pressure_points,
            )
        )

    return suspects


def _build_generated_case(
    *,
    theme_key: str,
    seed: int,
    title_override: str | None = None,
    origin: str = "generated",
    theme_override: ProceduralTheme | None = None,
    role_profiles: list[RoleProfile] | None = None,
    case_id_override: str | None = None,
    difficulty_label: str = "Процедурное",
    summary_hint_override: str | None = None,
) -> CaseFile:
    theme = theme_override or PROCEDURAL_THEMES[theme_key]
    profiles = role_profiles or ROLE_PROFILES
    rng = Random(f"{theme_key}:{seed}")
    venue_name = rng.choice(theme.venue_names)
    event_name = rng.choice(theme.events)
    victim_role = rng.choice(theme.victim_roles)
    restricted_area = rng.choice(theme.restricted_areas)
    public_area = rng.choice(theme.public_areas)
    side_area = rng.choice(theme.side_areas)
    document_name = rng.choice(theme.documents)
    trace_material = rng.choice(theme.traces)
    crime_object = rng.choice(theme.crime_objects)
    city = rng.choice(theme.locations)
    victim_name = _pick_names(rng, 1)[0]
    culprit_index = rng.randrange(len(profiles))
    red_herring_index = rng.choice([index for index in range(len(profiles)) if index != culprit_index])
    support_index = rng.choice(
        [index for index in range(len(profiles)) if index not in {culprit_index, red_herring_index}]
    )
    times = {
        "event": "19:10",
        "conflict": "19:46",
        "service": "20:34",
        "access": "21:08",
        "photo": "21:16",
        "discovery": "21:28",
    }
    culprit_name_list = _pick_names(rng, len(profiles))
    suspects = _build_generated_suspects(
        rng=rng,
        victim_name=victim_name,
        document_name=document_name,
        crime_object=crime_object,
        restricted_area=restricted_area,
        public_area=public_area,
        side_area=side_area,
        event_name=event_name,
        names=culprit_name_list,
        culprit_index=culprit_index,
        red_herring_index=red_herring_index,
        time_service=times["service"],
        time_photo=times["photo"],
        role_profiles=profiles,
    )
    culprit = suspects[culprit_index]
    red_herring = suspects[red_herring_index]
    support = suspects[support_index]
    culprit_first = culprit.name.split()[0]
    red_first = red_herring.name.split()[0]
    support_first = support.name.split()[0]
    victim_first = victim_name.split()[0]
    title = title_override or rng.choice(theme.title_templates).format(venue_name=venue_name)
    case_id = case_id_override or make_generated_case_id(theme_key, seed)

    introduction = (
        f"После {event_name} {victim_role} {victim_name} найден(а) без сознания у зоны «{restricted_area}». "
        f"Незадолго до инцидента {victim_first} собирался(ась) перепроверить {document_name} и упоминал(а) "
        f"пропажу вокруг {crime_object}. Внутри объекта слишком много людей со своими мотивами, "
        f"а ключевые маршруты проходят через служебные зоны, доступ к которым был только у персонала."
    )
    location = f"{city}, объект «{venue_name}»"
    timeline = [
        f"{times['event']} — начинается работа с {event_name}.",
        f"{times['conflict']} — {victim_first} спорит с несколькими сотрудниками из-за {document_name}.",
        f"{times['service']} — в зоне {side_area} фиксируют короткий служебный сбой.",
        f"{times['access']} — журнал допуска отмечает проход в {restricted_area}.",
        f"{times['photo']} — свидетель делает кадр у зоны {public_area}.",
        f"{times['discovery']} — тело {victim_first} обнаруживают рядом с {restricted_area}.",
    ]

    clues = [
        Clue(
            clue_id="access_log",
            title=f"Журнал доступа в «{restricted_area}»",
            description=(
                f"Система отмечает проход по служебной карте {culprit_first} в {times['access']}, "
                f"хотя в показаниях этот человек утверждает, что держался(ась) далеко от {restricted_area}."
            ),
            found_at=f"Панель контроля доступа у зоны {side_area}",
            interpretation=(
                f"Первое прямое давление на алиби {culprit_first}: доступ не доказывает нападение сам по себе, "
                "но рушит версию о полном отсутствии в служебной зоне."
            ),
            related_suspects=[culprit.suspect_id],
            misleading=False,
            critical=True,
            keywords=["доступ", "карта", restricted_area, times["access"], culprit_first],
        ),
        Clue(
            clue_id="camera_gap",
            title="Ручной разрыв видеозаписи",
            description=(
                f"Запись с камеры у {restricted_area} обрывается ровно на две минуты, а в журнале стоит ручной "
                f"сервисный запрос с поста, к которому имели доступ {culprit_first} и фигурант с ролью "
                f"«{suspects[1].role}»."
            ),
            found_at="Архив локальной системы наблюдения",
            interpretation=(
                "Это выглядит не как случайный сбой, а как вмешательство. Запись сама по себе не называет виновного, "
                "но показывает, что окно для скрытого перемещения было создано вручную."
            ),
            related_suspects=[culprit.suspect_id, suspects[1].suspect_id],
            misleading=False,
            critical=True,
            keywords=["камера", "сбой", "ручной", "архив", culprit_first],
        ),
        Clue(
            clue_id="trace_material",
            title=f"Следы вещества: {trace_material}",
            description=(
                f"На полу рядом с жертвой и на манжете {culprit_first} найден один и тот же след: {trace_material} "
                f"из зоны {restricted_area}."
            ),
            found_at=f"Пол у {restricted_area} и рукав подозреваемого",
            interpretation=(
                f"Материал физически связывает {culprit_first} с местом преступления. Это одна из самых надёжных улик "
                "в деле, потому что совпадает и по месту, и по времени."
            ),
            related_suspects=[culprit.suspect_id],
            misleading=False,
            critical=True,
            keywords=[trace_material, "манжета", "след", restricted_area, culprit_first],
        ),
        Clue(
            clue_id="document_draft",
            title=document_name.capitalize(),
            description=(
                f"В черновике {document_name} обнаружены недавние правки, ведущие к строке, выгодной именно {culprit_first}. "
                f"Жертва оставил(а) пометку: «сверить ночью до закрытия». "
            ),
            found_at=f"Папка документов у зоны {side_area}",
            interpretation=(
                f"Улика даёт ясный мотив: {victim_first} собирался(ась) вскрыть неформальную правку, "
                f"из-за которой {culprit_first} мог(ла) потерять деньги, должность или доступ."
            ),
            related_suspects=[culprit.suspect_id],
            misleading=False,
            critical=True,
            keywords=[document_name, "правка", "сверить", culprit_first, "ночью"],
        ),
        Clue(
            clue_id="witness_photo",
            title=f"Кадр у зоны «{public_area}»",
            description=(
                f"На снимке, сделанном в {times['photo']}, отчётливо видны {support_first} и толпа гостей, "
                f"но нет {culprit_first}, хотя по словам подозреваемого именно там он(а) якобы находился(лась)."
            ),
            found_at=f"Телефон свидетеля из зоны {public_area}",
            interpretation=(
                f"Фото не показывает сам момент преступления, но разбивает алиби {culprit_first} по времени. "
                "Если человек не там, где заявляет, значит нужно искать его маршрут в служебной части объекта."
            ),
            related_suspects=[culprit.suspect_id, support.suspect_id],
            misleading=False,
            critical=True,
            keywords=["фото", public_area, times["photo"], culprit_first, support_first],
        ),
        Clue(
            clue_id="key_hook",
            title="Пустой крючок запасного ключа",
            description=(
                f"В шкафу службы обнаружен пустой крючок и свежая смазка. Следы указывают, что запасной ключ "
                f"к {restricted_area} недавно снимали вручную."
            ),
            found_at="Шкаф служебных ключей",
            interpretation=(
                "Ключ не называет виновного автоматически, но подтверждает подготовку и знание внутренних маршрутов. "
                "Эта улика особенно сильна в связке с журналом доступа и следами вещества."
            ),
            related_suspects=[culprit.suspect_id, suspects[1].suspect_id, suspects[0].suspect_id],
            misleading=False,
            critical=True,
            keywords=["ключ", "крючок", "смазка", restricted_area],
        ),
        Clue(
            clue_id="heated_message",
            title="Резкое сообщение накануне",
            description=(
                f"В рабочем чате найдено сообщение, где {red_first} жёстко спорит с жертвой и обещает «не дать "
                f"сломать {event_name} к утру»."
            ),
            found_at="Экспорт внутреннего чата",
            interpretation=(
                f"Даёт мотив для {red_first}, но не привязывает его(её) к месту преступления. Это хороший ложный след: "
                "эмоции есть, физического маршрута нет."
            ),
            related_suspects=[red_herring.suspect_id],
            misleading=True,
            critical=False,
            keywords=["сообщение", red_first, event_name, "утру"],
        ),
        Clue(
            clue_id="service_note",
            title="Служебная отметка по дежурству",
            description=(
                f"В журнале дежурства указано, что {support_first} действительно находился(лась) у {public_area} "
                f"в момент снимка и подтверждает суету вокруг гостей."
            ),
            found_at="Журнал вечерней смены",
            interpretation=(
                f"Скорее поддерживает алиби {support_first} и делает снимок из {public_area} надёжнее. "
                "Улика нужна не ради сенсации, а чтобы отделить достоверный контекст от ложных версий."
            ),
            related_suspects=[support.suspect_id],
            misleading=False,
            critical=False,
            keywords=["дежурство", support_first, public_area, "журнал"],
        ),
    ]

    contradictions = [
        Contradiction(
            contradiction_id="access_vs_alibi",
            title="Алиби не сходится с журналом доступа",
            description=(
                f"{culprit_first} настаивает, что держался(ась) у {public_area}, однако журнал фиксирует его(её) "
                f"проход в {restricted_area} в {times['access']}."
            ),
            suspect_ids=[culprit.suspect_id],
            clue_ids=["access_log"],
            severity=5,
        ),
        Contradiction(
            contradiction_id="photo_vs_presence",
            title="Фото ломает версию о присутствии в открытой зоне",
            description=(
                f"По словам {culprit_first}, он(а) не отходил(а) от {public_area}, но кадр из {times['photo']} "
                f"не показывает его(её) рядом с местом, где алиби подтверждают другие люди."
            ),
            suspect_ids=[culprit.suspect_id, support.suspect_id],
            clue_ids=["witness_photo", "service_note"],
            severity=4,
        ),
        Contradiction(
            contradiction_id="trace_vs_denial",
            title="Физический след против слов",
            description=(
                f"{culprit_first} отрицает маршрут к {restricted_area}, однако {trace_material} связывает его(её) "
                "и с местом нападения, и со служебной зоной."
            ),
            suspect_ids=[culprit.suspect_id],
            clue_ids=["trace_material"],
            severity=5,
        ),
    ]

    motive_text = (
        f"{culprit_first} скрывал(а) манипуляцию вокруг {document_name} и {crime_object}. "
        f"{victim_first} собирался(ась) проверить документы ещё ночью, а значит вскрыть мотив, "
        "маршрут и финансовую выгоду прежде, чем подозреваемый успеет всё переписать к утру."
    )

    solution = Solution(
        culprit_id=culprit.suspect_id,
        culprit_name=culprit.name,
        motive=motive_text,
        key_evidence=[
            clues[0].title,
            clues[1].title,
            clues[2].title,
            clues[3].title,
            clues[4].title,
            clues[5].title,
        ],
        contradictions=[item.description for item in contradictions],
        logical_explanation=(
            f"Логика сходится на {culprit_first}: у него(неё) был мотив, доступ, окно в камерах и физический след, "
            f"ведущий прямо к {restricted_area}. Остальные подозреваемые либо имеют только эмоциональный конфликт, "
            "либо, наоборот, получают подтверждение своего алиби через журнал и фото."
        ),
        motive_keywords=["провер", "правк", "документ", "ночью", "долг", "доступ", crime_object],
        evidence_keywords={
            "access_log": ["доступ", "карта", times["access"], restricted_area],
            "camera_gap": ["камера", "сбой", "ручной", "архив"],
            "trace_material": [trace_material, "след", "манжета", restricted_area],
            "document_draft": [document_name, "правка", "сверить", "ночью"],
            "witness_photo": ["фото", public_area, times["photo"], culprit_first],
            "key_hook": ["ключ", "крючок", "смазка", restricted_area],
        },
    )

    return CaseFile(
        case_id=case_id,
        title=title,
        introduction=introduction,
        location=location,
        timeline=timeline,
        victim_name=victim_name,
        difficulty_label=difficulty_label,
        summary_hint=summary_hint_override or (
            "В процедурных делах особенно полезно сверять алиби с маршрутами и искать одну улику, "
            "которая одновременно даёт мотив и физическую привязку."
        ),
        suspects=suspects,
        clues=clues,
        contradictions=contradictions,
        solution=solution,
        origin=origin,
        generator_seed=seed,
        generator_theme=theme.key,
        generator_theme_label=theme.label,
    )


def build_generated_case(theme_key: str, seed: int) -> CaseFile:
    return _build_generated_case(theme_key=theme_key, seed=seed, origin="generated")


def _build_custom_role_profiles(role_names: list[str]) -> list[RoleProfile]:
    profiles: list[RoleProfile] = []
    for index, role_name in enumerate(role_names):
        base = ROLE_PROFILES[index % len(ROLE_PROFILES)]
        role_key = f"custom_{index}_{_slug(role_name)}"
        profiles.append(
            RoleProfile(
                key=role_key,
                role=role_name,
                backstory_templates=[
                    f"В этой истории роль «{role_name}» даёт доступ к людям, расписанию и скрытым маршрутам.",
                    f"Работает как «{role_name}» и знает, какие детали авторской темы лучше не выносить наружу.",
                ],
                motive_templates=[
                    f"Жертва собиралась проверить {{document_name}} и могла раскрыть личную схему, связанную с ролью «{role_name}».",
                    f"После конфликта вокруг {{crime_object}} боялся(ась), что жертва публично разрушит его(её) положение.",
                ],
                alibi_templates=[
                    "Утверждает, что с {time_service} до {time_photo} держался(ась) у {public_area}, потому что там все могли его(её) видеть.",
                    "Говорит, что в критический промежуток был(а) между {public_area} и {side_area}, решая проблему события.",
                ],
                secret_templates=[
                    f"Скрывал(а) частную договорённость, которую роль «{role_name}» позволяла провести без лишних свидетелей.",
                    "Без записи заходил(а) в {restricted_area}, хотя теперь называет это обычной рабочей проверкой.",
                ],
                fact_templates=[
                    f"Именно роль «{role_name}» объясняет, почему этот человек знал внутренние маршруты объекта.",
                    "Его(её) имя встречается в рабочей переписке рядом с темой {document_name}.",
                ],
                relationship_templates=[
                    f"С жертвой был напряжённый рабочий контакт: роль «{role_name}» давала влияние, но не защищала от проверки.",
                    "Жертва считала этого человека полезным, пока не начала перепроверять его(её) решения лично.",
                ],
                speaking_styles=base.speaking_styles,
                strategy_templates=[
                    "Держаться за свою роль и объяснять несостыковки хаосом авторской темы.",
                    "Признавать мелкие нарушения, но не подпускать следователя к мотиву и закрытой зоне.",
                ],
                pressure_points=list(dict.fromkeys(base.pressure_points + [_slug(role_name)]))[:4],
                trait_sets=base.trait_sets,
            )
        )
    return profiles


def build_custom_case(payload: dict[str, Any], seed: int) -> CaseFile:
    normalized = normalize_custom_theme_payload(payload)
    case_id = make_custom_case_id(normalized, seed)
    theme_key = f"custom_{_custom_theme_fingerprint(normalized)}"
    venue_name = normalized["venue_name"]
    case_title = normalized["case_title"]
    theme = ProceduralTheme(
        key=theme_key,
        label=normalized["theme_label"],
        pitch=normalized["pitch"],
        title_templates=[
            case_title or f"Тайна объекта «{venue_name}»",
            case_title or f"Последняя ночь в «{venue_name}»",
            case_title or f"Следы внутри «{venue_name}»",
        ],
        venue_names=[venue_name],
        locations=[normalized["location"]],
        events=[normalized["event_name"]],
        victim_roles=[normalized["victim_role"]],
        restricted_areas=[normalized["restricted_area"]],
        public_areas=[normalized["public_area"]],
        side_areas=[normalized["side_area"]],
        documents=[normalized["document_name"]],
        traces=[normalized["trace_material"]],
        crime_objects=[normalized["crime_object"]],
    )
    return _build_generated_case(
        theme_key=theme.key,
        seed=seed,
        title_override=case_title or None,
        origin="generated",
        theme_override=theme,
        role_profiles=_build_custom_role_profiles(normalized["suspect_roles"]),
        case_id_override=case_id,
        difficulty_label="Кастомное дело",
        summary_hint_override=(
            "В кастомных делах особенно внимательно смотрите на пользовательские детали темы: "
            "они превращаются в маршруты, мотивы и ключевые улики."
        ),
    )


def get_generation_themes() -> list[ProceduralTheme]:
    return list(PROCEDURAL_THEMES.values())


MIDNIGHT_GALLERY = CaseFile(
    case_id="midnight_gallery",
    title="Тень над галереей «Орбита»",
    introduction=(
        "После закрытого благотворительного показа владелец галереи Роман Лебедев найден у архивной лестницы. "
        "За несколько минут до этого он собирался перепроверить страховой пакет и сверить номер слепка "
        "бронзовой скульптуры «Ноктюрн», вокруг которой уже весь вечер пахло подменой."
    ),
    location="Санкт-Петербург, частная галерея современного искусства «Орбита»",
    timeline=[
        "19:00 — начинается закрытый показ для спонсоров и журналистов.",
        "19:37 — Роман резко спорит с реставратором у зоны хранения.",
        "20:58 — в архивном коридоре мигает свет и кратко зависает камера.",
        "21:11 — служебная карта открывает дверь в архив.",
        "21:18 — журналист делает фото главного зала.",
        "21:26 — тело Романа обнаруживают у лестницы.",
    ],
    victim_name="Роман Лебедев",
    difficulty_label="Авторское дело",
    summary_hint="Сверяйте страховые документы с тем, кто имел доступ к архиву и мог остаться вне главного зала.",
    suspects=[
        Suspect(
            suspect_id="alisa_karpova",
            name="Алиса Карпова",
            role="Реставратор галереи",
            short_backstory="Молодой реставратор, получивший в «Орбите» первый действительно крупный контракт.",
            personality_traits=["точная", "уязвлённая", "гордая"],
            speaking_style="Говорит коротко, профессиональными формулировками, раздражается от неточных слов.",
            motive="Роман собирался публично обвинить её в повреждении дорогостоящего полотна и лишить контракта.",
            alibi="Утверждает, что почти всё время работала в мастерской и готовила лак для срочного ремонта.",
            hidden_secrets=[
                "Без разрешения проводила ночной косметический ремонт спорной картины.",
                "Убрала из мастерской тряпки с растворителем, чтобы скрыть нарушение протокола.",
            ],
            known_facts=[
                "От одежды Алисы пахло растворителем.",
                "Она спорила с Романом около запасника до начала паники.",
            ],
            relationship_to_victim="Подчинённая и бывшая фаворитка Романа в профессиональном смысле.",
            stress_level=68,
            private_strategy="Признавать только технические ошибки и не позволять превратить их в мотив убийства.",
            pressure_points=["мастерская", "лак", "полотно"],
        ),
        Suspect(
            suspect_id="maksim_volkov",
            name="Максим Волков",
            role="Начальник охраны",
            short_backstory="Бывший военный, который знает объект как сеть маршрутов и допускает только те риски, которые сам контролирует.",
            personality_traits=["сдержанный", "жёсткий", "подозрительный"],
            speaking_style="Отвечает рублено и почти командным тоном.",
            motive="Роман грозил внутренним расследованием из-за слепых зон камер и левых клиентов вне договора.",
            alibi="Говорит, что в критический промежуток проверял грузовой вход и слушал доклады поста парковки.",
            hidden_secrets=[
                "Пустил в служебную зону машину одного из доноров без оформления.",
                "Не сразу доложил о сбое камеры у архивной двери.",
            ],
            known_facts=[
                "Имеет полный доступ к панели наблюдения.",
                "Его подпись стоит под финальным журналом инцидентов вечера.",
            ],
            relationship_to_victim="Нанятый силовой менеджер, с которым у Романа были постоянные конфликты.",
            stress_level=54,
            private_strategy="Давить на порядок и спорить не с фактами, а с тем, как следователь их трактует.",
            pressure_points=["камера", "пост", "журнал"],
        ),
        Suspect(
            suspect_id="vera_morozova",
            name="Вера Морозова",
            role="Заместитель директора",
            short_backstory="Правая рука владельца, которая держала на себе доноров, документы и тихие переговоры вне афиши.",
            personality_traits=["собранная", "ледяная", "расчётливая"],
            speaking_style="Говорит спокойно и официально, но слишком тщательно выбирает слова.",
            motive="Роман начал сверять страховой пакет и мог вскрыть выгодную ей схему вокруг подменённого слепка.",
            alibi="Утверждает, что в момент инцидента находилась в главном зале рядом с донорами и прессой.",
            hidden_secrets=[
                "Подменила копию скульптуры ещё до показа, рассчитывая закрыть дыру в финансах страховой выплатой.",
                "Лично отключала камеру через административную панель.",
            ],
            known_facts=[
                "Её служебная карта открывала архивную дверь в 21:11.",
                "На обуви Веры нашли бронзовую пыль из зоны хранения.",
            ],
            relationship_to_victim="Ближайшая управленческая союзница, которую Роман перестал безусловно прикрывать.",
            stress_level=79,
            private_strategy="Отрицать маршрут, признавать только управленческий конфликт и держать на виду прессу как алиби.",
            pressure_points=["страховка", "доноры", "архив"],
        ),
        Suspect(
            suspect_id="kirill_sedov",
            name="Кирилл Седов",
            role="Куратор выставки",
            short_backstory="Амбициозный куратор, который ждал от этого показа карьерного прорыва и слишком многое поставил на успех вечера.",
            personality_traits=["амбициозный", "нервный", "красноречивый"],
            speaking_style="Говорит длинно и красиво, пока разговор не касается провала.",
            motive="Роман собирался снять его с проекта после сорванных переговоров с художником.",
            alibi="Уверяет, что почти всё время был рядом с прессой и контролировал программу вечера.",
            hidden_secrets=[
                "Скрыл переписку о провальной доставке одной из работ.",
                "Просил Романа отложить внутренний скандал до конца показа.",
            ],
            known_facts=[
                "Именно Кирилл передавал журналистам изменённое расписание.",
                "Его имя фигурирует в поздней переписке с Романом.",
            ],
            relationship_to_victim="Соратник по публичной части проекта и вечный спорщик за кулисами.",
            stress_level=61,
            private_strategy="Признавать эмоциональный конфликт, но не подпускать к маршрутам и архиву.",
            pressure_points=["пресса", "расписание", "художник"],
        ),
    ],
    clues=[
        Clue(
            clue_id="gallery_access",
            title="Срабатывание карты доступа",
            description="Журнал доступа показывает вход по карте Веры Морозовой в архивный коридор в 21:11.",
            found_at="Панель допуска у архивной двери",
            interpretation="Разбивает её версию о непрерывном нахождении в главном зале.",
            related_suspects=["vera_morozova"],
            misleading=False,
            critical=True,
            keywords=["карта", "архив", "21:11", "вера"],
        ),
        Clue(
            clue_id="gallery_camera_gap",
            title="Пауза камеры №4",
            description="Запись у архивной лестницы прерывается ровно на две минуты после ручного входа в админ-панель.",
            found_at="Архив наблюдения",
            interpretation="Сбой был не случайным и потребовал административного доступа.",
            related_suspects=["vera_morozova", "maksim_volkov"],
            misleading=False,
            critical=True,
            keywords=["камера", "админ", "сбой", "архив"],
        ),
        Clue(
            clue_id="gallery_bronze",
            title="Бронзовая пыль",
            description="На обуви Веры и на рукаве жертвы обнаружена одинаковая бронзовая пыль со склада скульптур.",
            found_at="Обувь подозреваемой и одежда жертвы",
            interpretation="Даёт физическую привязку к зоне хранения и моменту контакта.",
            related_suspects=["vera_morozova"],
            misleading=False,
            critical=True,
            keywords=["бронза", "пыль", "склад", "вера"],
        ),
        Clue(
            clue_id="gallery_insurance",
            title="Черновик страхового акта",
            description="В папке документов найден страховой акт с пометками Романа и выгодной заменой номера слепка.",
            found_at="Стол заместителя директора",
            interpretation="Указывает на мотив: страховая схема вскрывалась именно в эту ночь.",
            related_suspects=["vera_morozova"],
            misleading=False,
            critical=True,
            keywords=["страховка", "слепок", "акт", "номер"],
        ),
        Clue(
            clue_id="gallery_photo",
            title="Фото из главного зала",
            description="На снимке журналиста в 21:18 есть гости и Кирилл, но нет Веры, хотя она утверждала обратное.",
            found_at="Камера журналиста",
            interpretation="Ломает алиби Веры по времени и месту.",
            related_suspects=["vera_morozova", "kirill_sedov"],
            misleading=False,
            critical=True,
            keywords=["фото", "21:18", "зал", "вера"],
        ),
        Clue(
            clue_id="gallery_solvent",
            title="Сильный растворитель",
            description="В мастерской Алисы найдены свежие следы растворителя на ткани и полу.",
            found_at="Реставрационная мастерская",
            interpretation="Даёт Алисе повод скрытничать, но не привязывает её к лестнице или архиву.",
            related_suspects=["alisa_karpova"],
            misleading=True,
            critical=False,
            keywords=["растворитель", "алиса", "мастерская"],
        ),
        Clue(
            clue_id="gallery_donor_chat",
            title="Переписка о донорах",
            description="Кирилл нервно просит Романа не срывать вечер из-за внутренней проверки.",
            found_at="Экспорт рабочего чата",
            interpretation="Показывает конфликт, но не даёт маршрута и физического следа.",
            related_suspects=["kirill_sedov"],
            misleading=True,
            critical=False,
            keywords=["кирилл", "вечер", "переписка"],
        ),
        Clue(
            clue_id="gallery_key",
            title="Пустой крючок запасного ключа",
            description="Запасной ключ от внутреннего архива снимали незадолго до паники.",
            found_at="Шкаф ключей",
            interpretation="Подтверждает подготовку и осознанный маршрут к архивной зоне.",
            related_suspects=["vera_morozova", "maksim_volkov"],
            misleading=False,
            critical=True,
            keywords=["ключ", "архив", "крючок", "маршрут"],
        ),
    ],
    contradictions=[
        Contradiction(
            contradiction_id="vera_access",
            title="Вера отрицает маршрут в архив",
            description="По словам Веры она не уходила из главного зала, но карта доступа ведёт её прямо к архиву.",
            suspect_ids=["vera_morozova"],
            clue_ids=["gallery_access"],
            severity=5,
        ),
        Contradiction(
            contradiction_id="vera_photo",
            title="Фото не подтверждает алиби",
            description="Снимок главного зала в 21:18 не показывает Веру там, где она клятвенно была.",
            suspect_ids=["vera_morozova", "kirill_sedov"],
            clue_ids=["gallery_photo"],
            severity=4,
        ),
        Contradiction(
            contradiction_id="vera_bronze",
            title="Физический след против слов",
            description="Бронзовая пыль связывает Веру с зоной хранения и телом жертвы, хотя она это отрицала.",
            suspect_ids=["vera_morozova"],
            clue_ids=["gallery_bronze"],
            severity=5,
        ),
    ],
    solution=Solution(
        culprit_id="vera_morozova",
        culprit_name="Вера Морозова",
        motive=(
            "Вера скрывала подмену слепка и готовила выгодную страховую выплату. Роман понял это, "
            "собрался сверить номер и разрушить схему ещё до конца вечера."
        ),
        key_evidence=[
            "Срабатывание карты доступа",
            "Пауза камеры №4",
            "Бронзовая пыль",
            "Черновик страхового акта",
            "Фото из главного зала",
            "Пустой крючок запасного ключа",
        ],
        contradictions=[
            "Её алиби рушится по карте доступа и фотографии.",
            "Физический след ведёт в складскую зону, а не в главный зал.",
            "Ручной сбой камеры совпадает с моментом её маршрута.",
        ],
        logical_explanation=(
            "Только Вера сочетает мотив, административный доступ, маршрут к архиву и физический контакт с местом нападения. "
            "Остальные фигуранты конфликтовали с Романом, но не могут собрать такую же цельную цепочку."
        ),
        motive_keywords=["страховка", "подмена", "слепок", "номер", "схема", "выплата"],
        evidence_keywords={
            "gallery_access": ["карта", "архив", "21:11", "вера"],
            "gallery_camera_gap": ["камера", "админ", "сбой", "ручной"],
            "gallery_bronze": ["бронза", "пыль", "склад", "рукав"],
            "gallery_insurance": ["страховка", "слепок", "акт", "номер"],
            "gallery_photo": ["фото", "21:18", "зал", "вера"],
            "gallery_key": ["ключ", "архив", "маршрут", "крючок"],
        },
    ),
)


PLATFORM_SEVEN = CaseFile(
    case_id="platform_seven",
    title="Последний рейс платформы №7",
    introduction=(
        "Начальника ночной смены Льва Захарова находят убитым в релейной комнате пригородного вокзала. "
        "За час до этого он оставил в журнале пометку о подозрительном списании оборудования и собирался "
        "проверить склад до конца смены."
    ),
    location="Пригородный вокзал, служебный блок платформы №7",
    timeline=[
        "21:55 — Лев спорит с машинистом Ярославом из-за дисциплинарного взыскания.",
        "22:03 — уборщица Нина начинает мыть главный зал перед закрытием.",
        "22:12 — диспетчер Ольга исправляет код рейса в журнале.",
        "22:14 — по станции звучит заранее записанное объявление.",
        "22:16 — машинист видит техника Тимура у сервисного коридора.",
        "22:19 — тело Льва находят в релейной комнате.",
    ],
    victim_name="Лев Захаров",
    difficulty_label="Авторское дело",
    summary_hint="Проверяйте не только конфликты на платформе, но и тех, кто понимал сервисные маршруты и ключи.",
    suspects=[
        Suspect(
            suspect_id="timur_belyaev",
            name="Тимур Беляев",
            role="Инженер по обслуживанию",
            short_backstory="Опытный техник, который отвечал за резервное питание и слишком вольно обращался со списанным оборудованием.",
            personality_traits=["ворчливый", "техничный", "закрытый"],
            speaking_style="Отвечает коротко и сухо, прячется за жаргоном и техническими деталями.",
            motive="Лев собирался проверить склад и увидеть, что Тимур списывает исправные преобразователи как неисправные.",
            alibi="Говорит, что в критическое время был на платформе №7 и контролировал световую линию.",
            hidden_secrets=[
                "Использовал сервисный тоннель, чтобы обходить камеры.",
                "Брал запасной ключ от релейной комнаты без записи в журнале.",
            ],
            known_facts=[
                "Именно его набором инструмента обслуживают узел рядом с релейной.",
                "Лев оставил в журнале пометку с инициалами «Т.Б.» перед смертью.",
            ],
            relationship_to_victim="Технический сотрудник, которого Лев собирался сдать служебной проверке.",
            stress_level=75,
            private_strategy="Прятаться за сложностью техники и делать вид, что любой след можно объяснить аварийным режимом.",
            pressure_points=["тоннель", "инструмент", "ключ"],
        ),
        Suspect(
            suspect_id="yaroslav_klinov",
            name="Ярослав Клинов",
            role="Машинист последнего рейса",
            short_backstory="Импульсивный машинист, которому грозило отстранение после серии конфликтов.",
            personality_traits=["вспыльчивый", "прямой", "самолюбивый"],
            speaking_style="Говорит громко и без дипломатии, но быстро устает от давления.",
            motive="Лев собирался временно снять его с линии после очередного опоздания и конфликта.",
            alibi="После прибытия состава курил у служебного выхода и ждал заполнения маршрутного листа.",
            hidden_secrets=[
                "Спорил с Львом гораздо резче, чем признаёт.",
                "Хотел сорваться на него повторно, но не успел из-за общей суматохи.",
            ],
            known_facts=[
                "Публично ругался с Львом перед половиной смены.",
                "Мог видеть сервисный коридор от служебного выхода.",
            ],
            relationship_to_victim="Подчинённый, регулярно конфликтовавший с начальником смены.",
            stress_level=66,
            private_strategy="Не отрицать злость, но не давать разговору уйти в маршруты и сервисные зоны.",
            pressure_points=["взыскание", "машинист", "угроза"],
        ),
        Suspect(
            suspect_id="olga_besedina",
            name="Ольга Беседина",
            role="Заместитель диспетчера",
            short_backstory="Сильный администратор станции, привыкший спасать смену правками в журналах и быстрыми решениями.",
            personality_traits=["аккуратная", "строгая", "нервная"],
            speaking_style="Формулирует точно и по пунктам, как на служебной записке.",
            motive="Лев собирался сорвать её перевод, если узнает о несанкционированной корректировке документов.",
            alibi="Исправляла код маршрута в журнале и сверяла данные в диспетчерской у момента убийства.",
            hidden_secrets=[
                "Иногда переписывала журналы задним числом, чтобы не портить статистику станции.",
                "Знала о бардаке с ключами, но закрывала на него глаза до проверки.",
            ],
            known_facts=[
                "Последняя работала с журналом смены до обнаружения тела.",
                "Хорошо знает, когда камеры пишут без звука.",
            ],
            relationship_to_victim="Коллега и соперница в управлении ночной сменой.",
            stress_level=58,
            private_strategy="Держаться за точность документов и признавать только бюрократические нарушения.",
            pressure_points=["журнал", "ключи", "диспетчерская"],
        ),
        Suspect(
            suspect_id="nina_chernyaeva",
            name="Нина Черняева",
            role="Уборщица вокзала",
            short_backstory="Старая сотрудница станции, которая замечает больше чужих маршрутов, чем многие дежурные.",
            personality_traits=["наблюдательная", "осторожная", "язвительная"],
            speaking_style="Говорит простыми образными фразами и не терпит высокомерия.",
            motive="Лев грозил написать жалобу за пропавший инвентарь, который она сама не брала.",
            alibi="Мыла главный зал непрерывно с ведром и шваброй, а пол в это время оставался мокрым без разрывов.",
            hidden_secrets=[
                "Слышала обрывок разговора Льва с Тимуром о списанном модуле.",
                "Нашла на полу болт, но сначала побоялась сдавать его как улику.",
            ],
            known_facts=[
                "Её мокрые следы тянутся через весь зал в момент убийства.",
                "Она видела техников у служебного коридора чаще других.",
            ],
            relationship_to_victim="Сотрудница вокзала, зависевшая от решений Льва по смене.",
            stress_level=50,
            private_strategy="Отвечать простыми фактами и не позволять сделать из неё удобный фон для чужой схемы.",
            pressure_points=["следы", "ведро", "зал"],
        ),
    ],
    clues=[
        Clue(
            clue_id="platform_tunnel_mud",
            title="Глина из сервисного тоннеля",
            description="На подошве Тимура и на полу у релейной комнаты найден одинаковый след серой глины из служебного тоннеля.",
            found_at="Пол у релейной и обувь подозреваемого",
            interpretation="Показывает маршрут Тимура к закрытой служебной зоне.",
            related_suspects=["timur_belyaev"],
            misleading=False,
            critical=True,
            keywords=["глина", "тоннель", "тимур", "подошва"],
        ),
        Clue(
            clue_id="platform_announcement",
            title="Лог служебного объявления",
            description="Система показывает, что объявление 22:14 было запущено заранее с терминала, а не вживую.",
            found_at="Системный журнал станции",
            interpretation="Ломает алиби Тимура о том, что он был занят у платформы и говорил в микрофон лично.",
            related_suspects=["timur_belyaev"],
            misleading=False,
            critical=True,
            keywords=["объявление", "22:14", "терминал", "запись"],
        ),
        Clue(
            clue_id="platform_key_hook",
            title="Следы на крючке запасного ключа",
            description="Запасной ключ от релейной снимали после 22:00, на крючке остались смазка и графит.",
            found_at="Шкаф служебных ключей",
            interpretation="Подтверждает подготовленный маршрут и доступ к релейной комнате.",
            related_suspects=["timur_belyaev", "olga_besedina"],
            misleading=False,
            critical=True,
            keywords=["ключ", "крючок", "смазка", "релейная"],
        ),
        Clue(
            clue_id="platform_note",
            title="Запись Льва в журнале",
            description="На полях журнала Лев пишет: «Т.Б. снова списал преобразователь. Проверить склад».",
            found_at="Журнал ночной смены",
            interpretation="Даёт Тимуру прямой мотив: к утру его схему собирались вскрыть официально.",
            related_suspects=["timur_belyaev"],
            misleading=False,
            critical=True,
            keywords=["т.б.", "списал", "преобразователь", "склад"],
        ),
        Clue(
            clue_id="platform_fiber",
            title="Волокно синей ветоши",
            description="На гаечном ключе у тела найдено волокно из синей технической ветоши Тимура.",
            found_at="Пол у релейной комнаты",
            interpretation="Связывает инструмент и комплект Тимура с местом нападения.",
            related_suspects=["timur_belyaev"],
            misleading=False,
            critical=True,
            keywords=["ветошь", "ключ", "тимур", "синяя"],
        ),
        Clue(
            clue_id="platform_fine",
            title="Черновик взыскания",
            description="Лев действительно готовил дисциплинарный документ против Ярослава.",
            found_at="Личный шкаф начальника смены",
            interpretation="Даёт Ярославу мотив, но не маршрут к релейной комнате.",
            related_suspects=["yaroslav_klinov"],
            misleading=True,
            critical=False,
            keywords=["взыскание", "ярослав", "документ"],
        ),
        Clue(
            clue_id="platform_clean_floor",
            title="Непрерывный мокрый след",
            description="Следы Нины тянутся через главный зал без разрыва в интервале 22:09–22:17.",
            found_at="Главный зал вокзала",
            interpretation="Поддерживает алиби Нины: незаметно уйти в релейную и вернуться она не успевала.",
            related_suspects=["nina_chernyaeva"],
            misleading=False,
            critical=False,
            keywords=["мокрый", "нина", "22:09", "зал"],
        ),
        Clue(
            clue_id="platform_route_fix",
            title="Исправление в маршрутном журнале",
            description="Ольга вносила правку в код рейса в 22:12 и оставила под ней свою подпись.",
            found_at="Диспетчерский журнал",
            interpretation="Скорее поддерживает её рабочее алиби, чем делает подозреваемой.",
            related_suspects=["olga_besedina"],
            misleading=False,
            critical=False,
            keywords=["ольга", "22:12", "подпись", "журнал"],
        ),
    ],
    contradictions=[
        Contradiction(
            contradiction_id="timur_announcement",
            title="Тимур не мог объявлять вживую",
            description="Он уверяет, что сам говорил по станции, но лог показывает заранее запущенную запись.",
            suspect_ids=["timur_belyaev"],
            clue_ids=["platform_announcement"],
            severity=5,
        ),
        Contradiction(
            contradiction_id="timur_tunnel",
            title="Маршрут ведёт не к платформе",
            description="Следы глины и наблюдение Ярослава ведут Тимура к сервисному коридору, а не к платформе №7.",
            suspect_ids=["timur_belyaev", "yaroslav_klinov"],
            clue_ids=["platform_tunnel_mud"],
            severity=4,
        ),
        Contradiction(
            contradiction_id="timur_trace",
            title="Физическая улика сильнее слов",
            description="Волокно и ключ связывают комплект Тимура с релейной сильнее, чем любое его объяснение про ремонт.",
            suspect_ids=["timur_belyaev"],
            clue_ids=["platform_fiber", "platform_key_hook"],
            severity=5,
        ),
    ],
    solution=Solution(
        culprit_id="timur_belyaev",
        culprit_name="Тимур Беляев",
        motive=(
            "Тимур скрывал схему со списанием исправных преобразователей и продажей их как неисправных. "
            "Лев собрался проверить склад и сделать это официальной служебной проверкой."
        ),
        key_evidence=[
            "Глина из сервисного тоннеля",
            "Лог служебного объявления",
            "Следы на крючке запасного ключа",
            "Запись Льва в журнале",
            "Волокно синей ветоши",
        ],
        contradictions=[
            "Его алиби ломается логом объявления.",
            "Сервисный тоннель ведёт к релейной, а не к платформе.",
            "Физические следы и ключ собирают цельную цепочку именно вокруг Тимура.",
        ],
        logical_explanation=(
            "Только Тимур сочетает мотив, доступ к релейной, маршрут через тоннель и физические улики на месте. "
            "У остальных есть конфликты, но нет совпадающей цепочки времени, доступа и следов."
        ),
        motive_keywords=["списал", "преобразователь", "склад", "проверка", "деньги", "схема"],
        evidence_keywords={
            "platform_tunnel_mud": ["глина", "тоннель", "тимур", "подошва"],
            "platform_announcement": ["объявление", "22:14", "терминал", "запись"],
            "platform_key_hook": ["ключ", "крючок", "смазка", "релейная"],
            "platform_note": ["т.б.", "списал", "преобразователь", "склад"],
            "platform_fiber": ["ветошь", "ключ", "тимур", "синяя"],
        },
    ),
)


CURATED_GENERATED_CASES = [
    _build_generated_case(
        theme_key="mountain_hotel",
        seed=1042,
        title_override="Шум в зимнем отеле «Перевал»",
        origin="local",
    ),
    _build_generated_case(
        theme_key="science_lab",
        seed=2084,
        title_override="Последний протокол комплекса «Кварц»",
        origin="local",
    ),
    _build_generated_case(
        theme_key="tv_studio",
        seed=3157,
        title_override="Молчание после эфира «Полярис»",
        origin="local",
    ),
    _build_generated_case(
        theme_key="river_terminal",
        seed=4271,
        title_override="Туман над терминалом «Пятый рейд»",
        origin="local",
    ),
]


CASE_COLLECTION = [
    MIDNIGHT_GALLERY,
    PLATFORM_SEVEN,
    *CURATED_GENERATED_CASES,
]


def get_case_map() -> dict[str, CaseFile]:
    return {case.case_id: case for case in CASE_COLLECTION}


def get_default_case_id() -> str:
    return CASE_COLLECTION[0].case_id
