# Academic Schedule Generator

## Software Requirements & Implementation Specification v1.0

------------------------------------------------------------------------

# 1. Project Overview

## 1.1 Purpose

The system is a cross-platform desktop application built with Python and
Tkinter that automatically generates academic schedules based on
user-defined calendar templates, resource constraints, and scheduling
requirements.

The system targets academic institutions (primary domain) but is
designed with extensibility in mind.

------------------------------------------------------------------------

## 1.2 Core Problem

Generate a conflict-free schedule by assigning requirements (classes,
sessions) to time blocks while respecting:

-   calendar structure
-   resource constraints
-   block availability
-   session requirements

------------------------------------------------------------------------

## 1.3 Architecture Requirements

The system must implement:

-   MVC architecture
-   PostgreSQL database
-   SQLAlchemy data layer
-   Tkinter UI
-   Greedy scheduling algorithm (v1)
-   Block-based time model

------------------------------------------------------------------------

## 1.4 Time Model (Critical Design Decision)

The system does NOT use minute-based scheduling.

Time is represented using calendar blocks derived from user-defined day
templates.

Example:

08:30--09:15 TeachingBlock\
09:15--09:25 Break\
09:25--10:10 TeachingBlock

Scheduling occurs only inside TeachingBlocks.

------------------------------------------------------------------------

# 2. System Architecture

## 2.1 Layers

### Domain Layer

Business logic and models.

### Services Layer

Use-case logic.

### Repository Layer

Database access.

### Controller Layer

Application flow.

### View Layer

Tkinter UI.

------------------------------------------------------------------------

## 2.2 Project Structure

src/app/ domain/ services/ repositories/ controllers/ ui/ config/

------------------------------------------------------------------------

# 3. Core Domain Model

## 3.1 MarkType

Defines types of calendar segments.

Fields: - id - name - kind: ENUM("TEACHING", "BREAK") - duration_minutes

Rules: - BREAK cannot contain scheduled events. - TEACHING may contain
events.

------------------------------------------------------------------------

## 3.2 DayPattern

Fields: - id - name

DayPatternItem: - id - day_pattern_id - order_index - mark_type_id

------------------------------------------------------------------------

## 3.3 WeekPattern

Maps weekday → DayPattern.

Fields: - id - monday_pattern_id - tuesday_pattern_id - ... -
sunday_pattern_id

------------------------------------------------------------------------

## 3.4 CalendarPeriod

Fields: - id - start_date - end_date - week_pattern_id

------------------------------------------------------------------------

## 3.5 TimeBlock (Generated)

Fields: - id - date - start_timestamp - end_timestamp - block_kind
("TEACHING", "BREAK") - order_in_day - day_of_week

------------------------------------------------------------------------

## 3.6 Resource

Fields: - id - name - type ENUM("TEACHER","ROOM","GROUP","SUBGROUP")

Constraint: Resource cannot be assigned to multiple events in same
TimeBlock.

------------------------------------------------------------------------

## 3.7 Requirement

Fields: - id - name - duration_blocks - sessions_total - max_per_week

------------------------------------------------------------------------

## 3.8 RequirementResource

Fields: - requirement_id - resource_id - role

------------------------------------------------------------------------

## 3.9 ScheduleEntry (Result)

Fields: - id - requirement_id - start_block_id - blocks_count

------------------------------------------------------------------------

# 4. Scheduling Rules

## 4.1 Hard Constraints

-   resource uniqueness per block
-   TEACHING blocks only
-   required consecutive blocks available
-   session count satisfied

------------------------------------------------------------------------

# 5. Scheduler Algorithm v1

## 5.1 Candidate Generation

For each Requirement: 1. Select all TEACHING TimeBlocks. 2. Filter
blocks where: - required resources are free - enough consecutive blocks
exist 3. Produce candidate list.

------------------------------------------------------------------------

## 5.2 Placement Strategy

Greedy: 1. Sort requirements by difficulty. 2. Select first valid
candidate. 3. Reserve blocks.

------------------------------------------------------------------------

# 6. Phase Implementation Plan

PHASE 0 --- Project Foundation - Project initialization - PostgreSQL
connection - SQLAlchemy setup - Alembic migrations - MVC structure

PHASE 1 --- Calendar Template System - MarkType - DayPattern -
WeekPattern - CalendarPeriod - TimeBlock generation

PHASE 2 --- Resource Management - Resource model - Resource CRUD

PHASE 3 --- Requirement System - Requirement model - RequirementResource

PHASE 4 --- Scheduler Engine - Conflict detection - Candidate
generation - Greedy placement

PHASE 5 --- Schedule Visualization - Weekly grid view

PHASE 6 --- Validation - Conflict checking

------------------------------------------------------------------------

# 7. Template UI Spec v1 (UA)

## 7.1 Мета

Описати контракт для роботи з шаблонами так, щоб UI/Controller/Domain
працювали узгоджено і без двозначностей.

## 7.2 Рівні шаблонів

- Blocks (`MarkType`)
- Day Templates (`DayPattern`)
- Week Templates (`WeekPattern`)

`CalendarPeriod`/Semester поки не змінюється в межах цього плану.

## 7.3 Єдині правила зв'язків

- `DayPattern` використовує тільки `MarkType`.
- `WeekPattern` використовує тільки `DayPattern`.
- Видалення сутностей, що вже використовуються, замінюється на
  архівацію (soft delete / archived state).

## 7.4 Політика linked vs snapshot

- У редакторах шаблонів використовується `linked` модель.
- `snapshot` допускається лише при застосуванні шаблонів у
  `CalendarPeriod`.

## 7.5 Фази реалізації шаблонів

### Фаза 0 — Узгодити структуру (мінімальний контракт)

Ціль: чітко визначити рівні та UX-правила.

Результат:

- зафіксований документ "Template UI spec v1" (цей розділ),
- уточнені правила зв'язків та архівації.

### Фаза 1 — Дані + API контролера (без UI)

Ціль: щоб екран міг підтягнути все потрібне одним викликом.

Потрібен метод контролера:

- `load_templates_overview(company_id)` повертає:
  - список `MarkType`,
  - список `DayTemplate` (`name + day_pattern + derived preview stats`),
  - список `WeekTemplate` (`name + weekday->day_template_id + derived preview`).

CRUD (мінімум):

- `create/update/delete(archive) MarkType`,
- `create/update/delete(archive) DayTemplate`,
- `create/update/delete(archive) WeekTemplate`,
- `duplicate` для кожного рівня.

Результат: дані готові для побудови UI.

### Фаза 2 — Layout вкладки "Шаблони" (каркас)

Ціль: візуально правильно розкласти полиці та зробити скрол.

Вимоги:

- один scroll container на всю вкладку (`Canvas + inner frame`),
- зверху jump bar: `Блоки | Дні | Тижні` (клік -> скрол до секції),
- 3 секції (shelves):
  - header: `title + count + "+ Додати"`,
  - wrap grid: картки з авто-переносом.

Результат: гарний екран навіть без редагування (read-first каталог).

### Фаза 3 — Компоненти карток (UI-атомарки)

Ціль: уніфікувати вигляд і поведінку карток.

Типи карток (на базі `RoundedMotionCard`):

- `MarkTypeCard`,
- `DayTemplateCard` (mini timeline preview),
- `WeekTemplateCard` (mini 7-day preview).

Поведінка:

- ЛКМ -> `open editor`,
- `...` / ПКМ -> context menu (`Edit / Duplicate / Archive/Delete`).

Результат: каталог шаблонів виглядає як продукт.

### Фаза 4 — Модалка-редактор (універсальний каркас)

Ціль: одна модалка, різний контент для рівнів.

Діалог:

- `TemplateEditorDialog(mode, template_level, template_id=None)`.

Структура:

- Header: `title + level badge`,
- Body: 2 колонки:
  - ліва: поля (`name`, `kind/duration/start_time`, ...),
  - права: редактор (або placeholder),
- Footer:
  - `Cancel`,
  - `Save/Create`,
  - `Duplicate` (для edit),
  - `Archive/Delete` (для edit).

Результат: уніфікований вхід для block/day/week.

### Фаза 5 — Редактор Blocks (MarkType) — швидка перемога

Ціль: перший повністю завершений flow.

Вимоги:

- create/edit: `name`, `kind`, `duration_minutes`,
- валідація: `duration > 0`, `name` не порожній,
- при delete:
  - якщо використовується у `DayPattern` -> archive або заборона hard delete.

Результат: рівень Blocks завершений end-to-end.

### Фаза 6 — Редактор Day Template (drag&drop MarkTypes)

Ціль: ручне моделювання шаблону дня.

У модалці (права частина):

- палітра `MarkType` (chips/mini cards),
- timeline list:
  - вставка `MarkType`,
  - reorder (drag рядків),
  - видалення слота,
- derived preview:
  - часові діапазони від `08:30`,
  - сумарна тривалість дня.

Швидкі дії:

- `Очистити`,
- `Додати Break між Teaching` (optional),
- `Зразок 45/10` (optional preset).

Результат: `DayPattern` повноцінно редагується в UI.

### Фаза 7 — Редактор Week Template (drag&drop DayTemplates)

Ціль: складання тижня з day templates.

У модалці:

- список `DayTemplate` (ліва панель),
- 7 колонок weekday,
- drag day-template -> assign weekday.

Кнопки:

- `Mon-Fri = X`,
- `Скопіювати Пн на інші`,
- `Sat/Sun вихідні`.

Валідація:

- кожен день тижня має бути assigned або explicit `Empty Day`.

Результат: `WeekPattern` збирається без ручного SQL/JSON.

### Фаза 8 — Залежності, архівація і "не ламай використане"

Ціль: безпечний продакшн UX.

Правила:

- `MarkType`: якщо використовується -> тільки archive,
- `DayTemplate`: якщо використовується у `WeekTemplate` -> archive або
  `duplicate & edit`,
- `WeekTemplate`: якщо використовується у `CalendarPeriod` -> archive +
  попередження.

Додатково:

- на картці показати `Used in: N`,
- у контекстному меню `Delete` замінити на `Archive`, якщо `N > 0`.

Результат: неможливо випадково зламати вже застосовані шаблони.

### Фаза 9 — Полірування вкладки

Ціль: довести до якісного продуктового вигляду.

Вимоги:

- пошук + фільтри в кожній секції,
- сортування: `A-Z / newest / most used`,
- порожні стани (empty states),
- toaster/snackbar: `Збережено`, `Дубль створено`,
- skeleton/loading (мінімум: `Loading...`).

Результат: вкладка "Шаблони" UX-ready.

### Фаза 10 — Тести (мінімум критичного)

Ціль: не допустити регресій.

Покриття:

- CRUD для `DayTemplate/WeekTemplate`,
- валідація залежностей (не можна hard delete, якщо є використання),
- `duplicate` створює незалежну копію (особливо `day_pattern_items`).

Результат: стабільність основних сценаріїв шаблонів.

------------------------------------------------------------------------

END OF SPEC
