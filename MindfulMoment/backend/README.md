# MindfulMoment API

Backend for the MindfulMoment Angular app. Implements all `/api` endpoints used by `data.service.ts` and `auth.service.ts`.

## Setup

```bash
cd backend
npm install
```

## Run

```bash
npm start
```

Server runs at `http://localhost:3001`. On first run, if `data/store.json` does not exist, data is seeded from `../mindful-moment-angular/src/assets/storage.json`.

## Using with Angular

1. Start the API: `cd backend && npm start`
2. Start Angular: `cd mindful-moment-angular && ng serve`
3. Open `http://localhost:4200`; `/api` requests are proxied to the backend.

## Data

- Persistence: `data/store.json` (created automatically).
- Structure matches the Angular `storage.json` shape: `users`, `communityGroups`, `safetyTips`, `emergencyContacts`.
