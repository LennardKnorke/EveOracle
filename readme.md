# EveOracle

> **Work in Progress**  
> A random idea that turned into a project to learn React.

## Overview

EveOracle is an intelligence interface for the MMORPG **EVE Online**. It combines data from **zKillboard** and **EVE's ESI API** into a single interface, making it easier to assess pilots and fleets at a glance.

### Planned Features

- Overview of own fleet composition
- Automatically update fleet
- Interface to manage *Allies*, *Neutrals*, and *Enemies*.
- Access Zkillboard data of players of interest
- Ability to assign, or note ships that are not part of fleet (likely enemies)
- Prediction Network for combat encounter

### Next Steps:
1. Button for Update Fleet - Fetch fleet information, players, and their ships
2. Review localt chat paste to retrieve all other pilots data
3. UI management to switch players between *Allies*, *Neutrals*, and *Enemies*.
4. Review zkill api fetching for efficiency

## Tech Stack

### Backend
- **FastAPI**

### Frontend
- **React**

### Database
- **MySQL** - Manage users

### Worker
- **Python** - Runs background tasks, saves historic data and updates prices. Write access to static data

## Project Status

This project is actively under development and serves as both a useful EVE Online tool and a learning project for React, FastAPI, and machine learning.