const functions = require("firebase-functions");
const admin = require("firebase-admin");
const axios = require("axios");

admin.initializeApp();

exports.triggerCloudRun = functions.firestore
    .document("timetableLAB_request/{docId}")
    .onCreate(async (snap, context) => {
        const data = snap.data();
        if (data.status !== "pending") return;

        const cloudRunURL = "https://your-cloud-run-url/run-timetable";  // Replace with actual URL

        try {
            const response = await axios.post(cloudRunURL, { year: data.year, type: data.type });
            await snap.ref.update({ status: "processing", run_id: response.data.run_id });
        } catch (error) {
            console.error("Error triggering Cloud Run:", error);
            await snap.ref.update({ status: "failed" });
        }
    });
