import time
import requests

API_URL = "http://localhost:8000/api/v1"

payload = {
    "title": "Test Demo Incident",
    "raw_text": "This is a demo incident regarding an AWS S3 bucket outage. The storage service went down for 30 minutes, causing a minor disruption to our internal dashboard.",
    "severity": "P3",
    "provider": "AWS"
}

def main():
    headers = {"X-API-Key": "dev-api-key-12345"}
    print("Submitting demo incident...")
    response = requests.post(f"{API_URL}/incidents", json=payload, headers=headers)
    if response.status_code != 201:
        print(f"Failed to create: {response.text}")
        exit(1)

    incident = response.json()
    incident_id = incident["id"]
    print(f"Created incident: {incident_id}")

    print("Waiting for workflow to start...")
    time.sleep(2)

    print("Polling run status...")
    max_polls = 30
    for _ in range(max_polls):
        res = requests.get(f"{API_URL}/runs/by-incident/{incident_id}", headers=headers)
        if res.status_code == 200:
            run_data = res.json()
            print(f"Run status: {run_data['status']}")
            if run_data['status'] in ['completed', 'failed', 'error']:
                print("Workflow finished!")
                break
        else:
            print(f"Error fetching run: {res.text}")
        time.sleep(2)

    print("Checking incident status...")
    inc_res = requests.get(f"{API_URL}/incidents/{incident_id}", headers=headers)
    if inc_res.status_code == 200:
        print(f"Final incident status: {inc_res.json()['status']}")


if __name__ == "__main__":
    main()
