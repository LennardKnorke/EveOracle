# EveOracle

> **Work in Progress**  
> A random idea that turned into a project to learn React.

## Overview

EveOracle is an intelligence interface for the MMORPG **EVE Online**. It combines data from **zKillboard** and **EVE's ESI API** into a single interface, making it easier to assess pilots and fleets at a glance.

### Current Features

- Fetches player and corporation data from ESI.
- Retrieves kill statistics from zKillboard.
- Consolidates information into a single view.
- Groups pilots by corporation and alliance.

### Planned Features

- Historical data collection for machine learning datasets.
- Dataset management tools.
- Model training interface.
- Combat outcome prediction for small-scale PvP engagements.
- Improved React-based dashboard and visualization.

## Tech Stack

### Backend

- **FastAPI**

#### Modules

- `app` – Main backend application.
- `esi` – Interface for ESI and zKillboard APIs.
- `datadesigner` – Creates datasets from historical data.
- `modelmanager` – Creates, deletes, and manages ML architectures.
- `training` – Trains models using generated datasets.

### Frontend

- **React**

### Database

- **MySQL**

## Project Status

This project is actively under development and serves as both a useful EVE Online tool and a learning project for React, FastAPI, and machine learning.