# How to Get Your Google API Credentials (`client_secret.json`)

This guide will walk you through the process of creating the `client_secret.json` file required for CampusScheduler to access your Google Calendar. This is a one-time setup that should take about 5-10 minutes.

### Why is this necessary?

To protect your privacy, Google requires any application that accesses your data (like your calendar) to be registered.

---

## Step 1: Create a New Google Cloud Project

Follow the steps detailed in the official [Google Cloud project guide](https://developers.google.com/workspace/guides/create-project) to create a Google Cloud Project.

The guide will assume you have named your project as `CampusScheduler` but you name it how you want.

## Step 2: Enable the Google Calendar API

In the [Google Cloud Console](https://console.cloud.google.com/):

1.  Make sure your new `CampusScheduler` project is selected in the top dropdown.
2.  Click the navigation menu (☰) in the top-left corner.
3.  Go to **APIs & Services > Library**.
4.  In the search bar, type `Google Calendar API` and press Enter.
5.  Click on the "Google Calendar API" result.
6.  Click the blue **"Enable"** button. Wait for it to finish.

---

## Step 3: Configure the OAuth Consent Screen

This screen is what Google would show you if you were logging in. Since this is a personal-use app, we only need to fill in the minimum required information.

1.  From the navigation menu (☰), go to **APIs & Services > OAuth consent screen**.
2.  Under "User Type", select **"External"** and click **"Create"**.
3.  On the next page ("Edit app registration"):
    *   **App name:** `CampusScheduler`
    *   **User support email:** Select your own email address from the dropdown.
    *   **Developer contact information:** Enter your own email address again.
    *   Click **"Save and Continue"**.
4.  **Scopes:** You can skip this page. Just click **"Save and Continue"**.
5.  **Test users:** This is a **critical step**. Because your app is not published, Google requires you to explicitly list the email addresses that are allowed to use it.
    *   Click **"+ Add Users"**.
    *   Enter the Google email address of the account whose calendar you want to sync. **This will be your own email address.**
    *   Click **"Add"**.
6.  Click **"Save and Continue"**. You'll land on a summary page. Click **"Back to Dashboard"**.

---

## Step 4: Create the OAuth Client ID

This is the final step where you actually generate the file.

1.  From the navigation menu (☰), go to **APIs & Services > Credentials**.
2.  At the top of the page, click **"+ Create Credentials"** and select **"OAuth client ID"**.
3.  On the "Create OAuth client ID" page:
    *   For **"Application type"**, select **"Desktop app"** from the dropdown menu.
    *   You can leave the name as the default.
    *   Click **"Create"**.

---

## Step 5: Download the `client_secret.json` File

1.  After clicking "Create", a dialog will appear saying "OAuth client created".
2.  Click the **"Download JSON"** button.
3.  A file will be downloaded. Its name will be something like `client_secret_[...].json`.
4.  **Rename this file to `client_secret.json`**.
5.  Keep this file somewhere safe on your computer. The `campsched config` setup wizard will ask you to save it in a specific location.

> **Important:** Treat this file like a password. Do not share it publicly or commit it to a public GitHub repository.

You are now done! You can close the Google Cloud Console and return to the CampusScheduler setup wizard.