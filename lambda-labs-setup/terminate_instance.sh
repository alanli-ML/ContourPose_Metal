#!/bin/bash
# Terminate Lambda Labs instance

echo "⚠️  This will terminate your Lambda Labs instance and stop all billing."
echo "🔄 Make sure to download any results you need first!"
echo ""
read -p "Are you sure you want to terminate the instance? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Termination cancelled"
    exit 0
fi

# Load API key
API_KEY=$(cat .env | cut -d'=' -f2)

echo "🔍 Getting instance ID..."
INSTANCE_ID=$(curl -s -H "Authorization: Bearer $API_KEY" \
  https://cloud.lambdalabs.com/api/v1/instances | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['data'][0]['id'])")

echo "🗑️  Terminating instance: $INSTANCE_ID"

curl -X POST \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"instance_ids\": [\"$INSTANCE_ID\"]}" \
  https://cloud.lambdalabs.com/api/v1/instance-operations/terminate

echo ""
echo "✅ Termination request sent!"
echo "💰 Billing has been stopped."
echo "🗂️  Any saved results should be downloaded before the instance is fully terminated."