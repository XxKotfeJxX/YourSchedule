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

END OF SPEC
