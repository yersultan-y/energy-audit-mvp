from flask import Flask, render_template, request, jsonify
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os

# 1. Force load variables from .env BEFORE reading os.getenv
load_dotenv(override=True)

app = Flask(__name__)

# 2. Fetch credentials and strip any hidden spaces/newlines
GMAIL_USER = os.getenv("GMAIL_USER", "").strip()
GMAIL_PASS = os.getenv("GMAIL_PASS", "").strip()

# Startup diagnostic check in VS Code Terminal
print("\n" + "="*50)
print(f"🔧 SMTP CONFIG CHECK:")
print(f"   - Loaded Email: '{GMAIL_USER}'")
print(f"   - App Pass Length: {len(GMAIL_PASS)} characters (Expected: 16)")
if len(GMAIL_PASS) != 16 and len(GMAIL_PASS) > 0:
    print("   ⚠️ WARNING: Password length is not 16. Ensure spaces are removed in .env!")
print("="*50 + "\n")

def calculate_energy_breakdown(monthly_cost_tenge, monthly_kwh, building_size_sqm):
    cost_per_kwh = monthly_cost_tenge / monthly_kwh if monthly_kwh > 0 else 0
    cost_per_sqm = monthly_cost_tenge / building_size_sqm if building_size_sqm > 0 else 0
    benchmark_cost_per_sqm = 75

    breakdown = {
        "monthly_cost": monthly_cost_tenge,
        "monthly_kwh": monthly_kwh,
        "cost_per_kwh": round(cost_per_kwh, 2),
        "cost_per_sqm": round(cost_per_sqm, 2),
        "benchmark_cost_per_sqm": benchmark_cost_per_sqm,
        "efficiency_score": round((benchmark_cost_per_sqm / cost_per_sqm * 100) if cost_per_sqm > 0 else 0, 1),
    }

   recommendations = []
    if cost_per_sqm > benchmark_cost_per_sqm * 1.2:
        pct_above = round(((cost_per_sqm / benchmark_cost_per_sqm - 1) * 100), 0)
        est_savings = round((cost_per_sqm - benchmark_cost_per_sqm) * building_size_sqm / 1000, 0)
        # Use round(cost_per_sqm, 2) inside the string:
        recommendations.append(f"⚠️ Your cost/sqm ({round(cost_per_sqm, 2)}₸) is {pct_above:.0f}% above average. Potential savings: {est_savings:,.0f}K₸/month")
    if monthly_kwh / building_size_sqm > 0.5:
        recommendations.append("💡 High energy intensity. Consider: LED retrofit, HVAC audit, insulation check")

    if not recommendations:
        recommendations.append("✅ Your energy efficiency is competitive. Monitor for seasonal peaks.")

    breakdown["recommendations"] = recommendations
    return breakdown

def send_email(customer_email, customer_name, breakdown):
    subject = f"Energy Audit Results - {customer_name}"
    recs = '\n'.join(['- ' + rec for rec in breakdown['recommendations']])
    body = f"""Hi {customer_name},

Here is your energy cost analysis:

📊 CURRENT STATE:
- Monthly cost: {breakdown['monthly_cost']:,.0f} ₸
- Monthly usage: {breakdown['monthly_kwh']:,.0f} kWh
- Cost per sqm: {breakdown['cost_per_sqm']} ₸ (Local Avg: {breakdown['benchmark_cost_per_sqm']} ₸)
- Efficiency score: {breakdown['efficiency_score']}%

🎯 RECOMMENDATIONS:
{recs}

💰 NEXT STEP:
Subscribe to monthly audits (350K ₸/month) to track savings and optimization opportunities.

---
Energy Analytics | Astana
"""
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = GMAIL_USER
        msg['To'] = customer_email

        # 3. Use Port 587 with STARTTLS for broad local OS compatibility
        print(f" Attempting SMTP delivery to {customer_email}...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(GMAIL_USER, GMAIL_PASS)
        server.send_message(msg)
        server.quit()
        print("✅ Email delivered successfully!")
        return True, "Success"
    except Exception as e:
        # Print detailed error to VS Code terminal
        print(f"\n❌ SMTP FAILURE: {type(e).__name__} -> {e}\n")
        return False, str(e)

@app.route('/')
def index():
    return render_template('form.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.json
    try:
        breakdown = calculate_energy_breakdown(
            float(data['monthly_cost']),
            float(data['monthly_kwh']),
            float(data['building_size'])
        )
        email_sent, error_msg = send_email(data['email'].strip(), data['name'].strip(), breakdown)
        
        if not email_sent:
            return jsonify({
                "success": False,
                "error": f"Email error: {error_msg}"
            }), 500

        return jsonify({
            "success": True,
            "breakdown": breakdown,
            "email_sent": email_sent,
            "message": f"Analysis sent to {data['email'].strip()}"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)