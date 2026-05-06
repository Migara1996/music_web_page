# Lambda + API Gateway Deployment Guide

## Overview

One Lambda function (`lambda_handler.py`) handles all routes. API Gateway is
configured with a resource per path, and each HTTP method routes to this same
function using Lambda Proxy Integration.

## API Gateway Resource Structure

```
REST API
└── /login          POST   → lambda_handler
└── /register       POST   → lambda_handler
└── /query          GET    → lambda_handler
└── /subscriptions  GET    → lambda_handler
└── /subscribe      POST   → lambda_handler
└── /remove         DELETE → lambda_handler
```

These paths match the existing Flask backend so the same `frontend/app.js`
can be reused — only `API_BASE_URL` needs to change.

Each resource also has an OPTIONS method (for CORS pre-flight) that routes to
the same Lambda function.

---

## Step 1 — Create the Lambda Function

1. Open the Lambda console → **Create function** → Author from scratch.
2. Function name: `music_app_lambda`
3. Runtime: Python 3.12
4. Execution role: **Use an existing role** → select `LabRole`
5. Click **Create function**.
6. In the **Code** tab, paste the contents of `lambda_handler.py` into the
   editor, replacing the default code.
7. Click **Deploy**.

---

## Step 2 — Test the Lambda Function

Use the **Test** tab with the following sample events.

**POST /login — valid credentials**
```json
{
  "httpMethod": "POST",
  "path": "/login",
  "queryStringParameters": null,
  "body": "{\"email\": \"s3916164@student.rmit.edu.au\", \"password\": \"password1\"}"
}
```

**GET /subscriptions**
```json
{
  "httpMethod": "GET",
  "path": "/subscriptions",
  "queryStringParameters": { "email": "s3916164@student.rmit.edu.au" },
  "body": null
}
```

**GET /query — search by artist**
```json
{
  "httpMethod": "GET",
  "path": "/query",
  "queryStringParameters": { "artist": "Taylor Swift" },
  "body": null
}
```

---

## Step 3 — Create the REST API in API Gateway

1. Open the API Gateway console → **Create API** → **REST API** → **Build**.
2. Choose **New API**. Name it `music-api`. Click **Create API**.

### Create resources and methods

Repeat for each path below. For every method:
- Integration type: **Lambda Function**
- Check **Use Lambda Proxy integration**
- Lambda function: `music_app_lambda`
- Click **Save** → **OK** when prompted to add permission.

| Resource path   | Methods to add  |
|-----------------|-----------------|
| `/login`        | POST, OPTIONS   |
| `/register`     | POST, OPTIONS   |
| `/query`        | GET, OPTIONS    |
| `/subscriptions`| GET, OPTIONS    |
| `/subscribe`    | POST, OPTIONS   |
| `/remove`       | DELETE, OPTIONS |

### Enable CORS (per resource)

For each resource, click **Actions** → **Enable CORS**.
- Access-Control-Allow-Origin: `'*'` (change to your S3 URL in production)
- Check all methods shown.
- Click **Enable CORS and replace existing CORS headers**.

---

## Step 4 — Deploy the API

1. Click **Actions** → **Deploy API**.
2. Stage name: `prod`.
3. Click **Deploy**.
4. Copy the **Invoke URL** shown at the top of the stage editor.
   It looks like: `https://<id>.execute-api.us-east-1.amazonaws.com/prod`

---

## Step 5 — Point the Frontend at the Lambda Backend

The existing `frontend/app.js` works as-is. Just update `API_BASE_URL` on
line 1 to your API Gateway Invoke URL (no trailing slash):

```js
const API_BASE_URL = "https://<id>.execute-api.us-east-1.amazonaws.com/prod";
```

Then re-upload `app.js` to the S3 bucket hosting the frontend. The HTML and
CSS files do not need changes.

---

## Production note on CORS

The Lambda function currently returns `Access-Control-Allow-Origin: *`.
For production, replace the wildcard with your S3 static website URL, e.g.:

```python
"Access-Control-Allow-Origin": "http://<bucket>.s3-website-us-east-1.amazonaws.com",
```

This restricts which origins may call the API and allows credential-bearing
requests if needed in future.
