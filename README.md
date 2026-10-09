# Berlin Apartment Alert Bot

**An AI-assisted Python automation project for housing data collection, filtering and Telegram notifications.**

## Overview

The Berlin Apartment Alert Bot is a personal software project designed to reduce the manual effort involved in searching for rental housing in Berlin. It monitors five configured housing-provider sources, processes listing information, applies configurable search criteria and sends matching results to a Telegram group.

The project demonstrates practical skills in Python development, data collection, automation, testing, version control and cloud deployment.

## Key Features

- Collects apartment listings from five configured providers.
- Extracts and processes listing information.
- Filters listings by rent, room count and excluded keywords.
- Tracks listings to help avoid repeated alerts.
- Sends formatted notifications through Telegram.
- Runs continuously on PythonAnywhere.
- Includes automated tests for core filtering behaviour.

## Technology Stack

- **Language:** Python
- **Data collection:** Requests, Beautiful Soup, feedparser
- **Configuration:** Environment variables and python-dotenv
- **Testing:** pytest
- **Notifications:** Telegram Bot API
- **Version control:** Git and GitHub
- **Deployment:** PythonAnywhere Always-on task

## Example Configuration

The current deployment uses these search criteria:

- Maximum rent: €1,500
- Room range: 1–3
- Exclusions: WG rooms and temporary rentals
- Sources: DEGEWO, GEWOBAG, GESOBAU, WBM and Berlinovo

These values are configurable and can be adapted to different housing-search requirements.

## Testing and Deployment

The project passed 29 automated tests during deployment verification. The application is deployed on PythonAnywhere and communicates with a dedicated Telegram group.

## Development Approach

AI-assisted programming tools supported parts of the development process. Project requirements, integration, configuration, debugging, testing and deployment were handled as part of the project workflow.

This project is a practical learning exercise in automation engineering and data processing. It does not currently claim to implement a machine-learning model.

## Future Improvements

- Add automated monitoring of provider failures.
- Improve data validation and listing normalisation.
- Expand test coverage for individual provider integrations.
- Add logging and reporting for feed health and newly discovered listings.
- Improve deployment documentation and operational reliability.

## Security

Telegram credentials and other private configuration values are stored in a local `.env` file and must never be committed to the repository.
