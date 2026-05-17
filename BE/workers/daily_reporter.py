#!/usr/bin/env python3
"""
Daily Reporter Worker (Milestone 16)

Generates and sends daily SMS campaign performance reports.
Should be scheduled to run daily at 11:59 PM via Windows Task Scheduler or cron.

Features:
- Generates daily statistics for all stores
- Sends HTML email report to configured recipients
- Tracks phone number health and usage
- Highlights issues and warnings

Usage:
    # Generate report for today
    python BE/workers/daily_reporter.py

    # Generate report for specific date
    python BE/workers/daily_reporter.py --date=2025-11-14

    # Send email report
    python BE/workers/daily_reporter.py --send-email

Windows Task Scheduler:
    schtasks /create /tn "SMS_DailyReport" /tr "python C:\path\to\BE\workers\daily_reporter.py --send-email" /sc daily /st 23:59
"""

import os
import sys
import argparse
import pyodbc
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

# SQL Server configuration
SQL_SERVER = os.getenv('SQLServer')
SQL_USER = os.getenv('SQLUser')
SQL_PASSWORD = os.getenv('SQLPassword')
SQL_DATABASE = os.getenv('SQLDatabase')

# Email configuration
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
REPORT_RECIPIENTS = os.getenv('REPORT_RECIPIENTS', 'gene@example.com').split(',')


class DailyReporter:
    """
    Generates daily SMS campaign performance reports.
    """
    
    def __init__(self):
        """Initialize the daily reporter."""
        self.connection_string = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"UID={SQL_USER};"
            f"PWD={SQL_PASSWORD}"
        )
    
    def get_db_connection(self):
        """Get database connection."""
        return pyodbc.connect(self.connection_string)
    
    def generate_report(self, date: Optional[datetime.date] = None) -> Dict[str, Any]:
        """
        Generate daily report for all stores.
        
        Args:
            date: Date to generate report for (default: today)
        
        Returns:
            Dict with report data
        """
        if date is None:
            date = datetime.now().date()
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            print(f"\n{'='*70}")
            print(f"Generating Daily Report for {date}")
            print(f"{'='*70}\n")
            
            # Get all active stores
            cursor.execute("""
                SELECT store_id, name, daily_sms_quota, daily_call_quota
                FROM stores
                WHERE is_active = 1
                ORDER BY store_id
            """)
            
            stores_data = []
            total_sms = 0
            total_calls = 0
            total_replies = 0
            total_yes = 0
            total_stop = 0
            stores_active = 0
            
            for store_row in cursor.fetchall():
                store_id = store_row[0]
                store_name = store_row[1]
                sms_quota = store_row[2] or 200
                call_quota = store_row[3] or 60
                
                # Count SMS for this store
                cursor.execute("""
                    SELECT COUNT(*) as sms_count
                    FROM OutboundLeads
                    WHERE store_id = ?
                      AND CAST(sms_consent_requested_at AS DATE) = ?
                """, store_id, date)
                
                sms_count = cursor.fetchone()[0]
                
                # Count calls for this store
                cursor.execute("""
                    SELECT COUNT(*) as call_count
                    FROM OutboundCallResults ocr
                    JOIN OutboundLeads ol ON ocr.lead_id = ol.lead_id
                    WHERE ol.store_id = ?
                      AND CAST(ocr.call_time AS DATE) = ?
                """, store_id, date)
                
                call_count = cursor.fetchone()[0]
                
                # Count replies by classification
                cursor.execute("""
                    SELECT 
                        SUM(CASE WHEN reply_classification = 'YES' THEN 1 ELSE 0 END) as yes_count,
                        SUM(CASE WHEN reply_classification = 'STOP' THEN 1 ELSE 0 END) as stop_count,
                        SUM(CASE WHEN reply_classification = 'OTHER' THEN 1 ELSE 0 END) as other_count
                    FROM sms_replies sr
                    JOIN OutboundLeads ol ON sr.lead_id = ol.lead_id
                    WHERE ol.store_id = ?
                      AND CAST(sr.received_at AS DATE) = ?
                """, store_id, date)
                
                reply_row = cursor.fetchone()
                yes_replies = reply_row[0] or 0
                stop_replies = reply_row[1] or 0
                other_replies = reply_row[2] or 0
                store_total_replies = yes_replies + stop_replies + other_replies
                
                # Calculate reply rate
                reply_rate = 0.0
                if sms_count > 0:
                    reply_rate = round((store_total_replies / sms_count) * 100, 1)
                
                # Check quota usage
                sms_quota_percent = round((sms_count / sms_quota) * 100, 1) if sms_quota > 0 else 0
                call_quota_percent = round((call_count / call_quota) * 100, 1) if call_quota > 0 else 0
                
                if sms_count > 0 or call_count > 0:
                    stores_active += 1
                
                total_sms += sms_count
                total_calls += call_count
                total_replies += store_total_replies
                total_yes += yes_replies
                total_stop += stop_replies
                
                stores_data.append({
                    'store_id': store_id,
                    'store_name': store_name,
                    'sms_sent': sms_count,
                    'sms_quota': sms_quota,
                    'sms_quota_percent': sms_quota_percent,
                    'calls_made': call_count,
                    'call_quota': call_quota,
                    'call_quota_percent': call_quota_percent,
                    'replies_yes': yes_replies,
                    'replies_stop': stop_replies,
                    'replies_other': other_replies,
                    'reply_rate': reply_rate
                })
                
                print(f"{store_name}:")
                print(f"  SMS Sent: {sms_count}/{sms_quota} ({sms_quota_percent}%)")
                print(f"  Calls Made: {call_count}/{call_quota} ({call_quota_percent}%)")
                print(f"  Replies: {store_total_replies} (Reply Rate: {reply_rate}%)")
            
            # Calculate overall reply rate
            overall_reply_rate = 0.0
            if total_sms > 0:
                overall_reply_rate = round((total_replies / total_sms) * 100, 1)
            
            print(f"\n{'='*70}")
            print(f"TOTAL ACROSS ALL STORES:")
            print(f"  SMS Sent: {total_sms}")
            print(f"  Calls Made: {total_calls}")
            print(f"  Total Replies: {total_replies}")
            print(f"  YES Replies: {total_yes}")
            print(f"  STOP Replies: {total_stop}")
            print(f"  Overall Reply Rate: {overall_reply_rate}%")
            print(f"  Stores Active: {stores_active}")
            print(f"{'='*70}\n")
            
            return {
                'date': date,
                'summary': {
                    'total_sms_sent': total_sms,
                    'total_calls_made': total_calls,
                    'total_replies': total_replies,
                    'yes_replies': total_yes,
                    'stop_replies': total_stop,
                    'reply_rate': overall_reply_rate,
                    'stores_active': stores_active
                },
                'stores': stores_data
            }
        
        finally:
            cursor.close()
            conn.close()
    
    def generate_html_email(self, report_data: Dict[str, Any]) -> str:
        """
        Generate HTML email from report data.
        
        Args:
            report_data: Report data dictionary
        
        Returns:
            HTML string
        """
        date = report_data['date']
        summary = report_data['summary']
        stores = report_data['stores']
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
        }}
        .summary-box {{
            background-color: #ecf0f1;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .summary-stat {{
            display: inline-block;
            margin: 10px 20px 10px 0;
        }}
        .summary-stat strong {{
            color: #2980b9;
            font-size: 24px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th {{
            background-color: #3498db;
            color: white;
            padding: 12px;
            text-align: left;
        }}
        td {{
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .quota-ok {{
            color: #27ae60;
        }}
        .quota-warning {{
            color: #f39c12;
        }}
        .quota-critical {{
            color: #e74c3c;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            font-size: 12px;
            color: #7f8c8d;
        }}
    </style>
</head>
<body>
    <h1>📊 Daily SMS Campaign Report</h1>
    <p><strong>Date:</strong> {date.strftime('%B %d, %Y')}</p>
    
    <div class="summary-box">
        <h2>📈 Overall Summary</h2>
        <div class="summary-stat">
            <div>SMS Sent</div>
            <strong>{summary['total_sms_sent']}</strong>
        </div>
        <div class="summary-stat">
            <div>Calls Made</div>
            <strong>{summary['total_calls_made']}</strong>
        </div>
        <div class="summary-stat">
            <div>Replies</div>
            <strong>{summary['total_replies']}</strong>
        </div>
        <div class="summary-stat">
            <div>Reply Rate</div>
            <strong>{summary['reply_rate']}%</strong>
        </div>
        <div class="summary-stat">
            <div>Stores Active</div>
            <strong>{summary['stores_active']}</strong>
        </div>
    </div>
    
    <h2>🏪 Store-by-Store Performance</h2>
    <table>
        <thead>
            <tr>
                <th>Store</th>
                <th>SMS Sent</th>
                <th>Calls Made</th>
                <th>Replies</th>
                <th>Reply Rate</th>
            </tr>
        </thead>
        <tbody>
"""
        
        for store in stores:
            # Determine quota status color
            sms_quota_class = 'quota-ok'
            if store['sms_quota_percent'] >= 90:
                sms_quota_class = 'quota-critical'
            elif store['sms_quota_percent'] >= 70:
                sms_quota_class = 'quota-warning'
            
            call_quota_class = 'quota-ok'
            if store['call_quota_percent'] >= 90:
                call_quota_class = 'quota-critical'
            elif store['call_quota_percent'] >= 70:
                call_quota_class = 'quota-warning'
            
            html += f"""
            <tr>
                <td><strong>{store['store_name']}</strong></td>
                <td class="{sms_quota_class}">{store['sms_sent']}/{store['sms_quota']} ({store['sms_quota_percent']}%)</td>
                <td class="{call_quota_class}">{store['calls_made']}/{store['call_quota']} ({store['call_quota_percent']}%)</td>
                <td>✅ {store['replies_yes']} | ❌ {store['replies_stop']} | 💬 {store['replies_other']}</td>
                <td>{store['reply_rate']}%</td>
            </tr>
"""
        
        html += """
        </tbody>
    </table>
    
    <div class="footer">
        <p>This is an automated daily report generated by the SMS Campaign Management System.</p>
        <p>For questions or issues, contact your system administrator.</p>
    </div>
</body>
</html>
"""
        
        return html
    
    def send_email_report(self, report_data: Dict[str, Any]):
        """
        Send email report to configured recipients.
        
        Args:
            report_data: Report data dictionary
        """
        if not SMTP_USER or not SMTP_PASSWORD:
            print("⚠️  Email configuration not set. Skipping email send.")
            print("   Set SMTP_USER and SMTP_PASSWORD in .env file to enable email reports.")
            return
        
        try:
            print(f"\n[Email] Sending report to: {', '.join(REPORT_RECIPIENTS)}")
            
            # Generate HTML content
            html_content = self.generate_html_email(report_data)
            
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Daily SMS Campaign Report - {report_data['date'].strftime('%B %d, %Y')}"
            msg['From'] = SMTP_USER
            msg['To'] = ', '.join(REPORT_RECIPIENTS)
            
            # Attach HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
            
            print(f"✅ Email report sent successfully!")
        
        except Exception as e:
            print(f"❌ Failed to send email report: {e}")
    
    def save_html_report(self, report_data: Dict[str, Any], output_path: str):
        """
        Save HTML report to file.
        
        Args:
            report_data: Report data dictionary
            output_path: Path to save HTML file
        """
        try:
            html_content = self.generate_html_email(report_data)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"✅ HTML report saved to: {output_path}")
        
        except Exception as e:
            print(f"❌ Failed to save HTML report: {e}")


def main():
    """Main entry point for daily reporter."""
    parser = argparse.ArgumentParser(description='Daily SMS Campaign Reporter')
    parser.add_argument(
        '--date',
        type=str,
        help='Date to generate report for (YYYY-MM-DD format, default: today)'
    )
    parser.add_argument(
        '--send-email',
        action='store_true',
        help='Send email report to configured recipients'
    )
    parser.add_argument(
        '--save-html',
        type=str,
        help='Save HTML report to file (specify output path)'
    )
    
    args = parser.parse_args()
    
    # Parse date or use today
    if args.date:
        try:
            target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        except ValueError:
            print(f"❌ Invalid date format: {args.date}")
            print("   Use YYYY-MM-DD format (e.g., 2025-11-14)")
            sys.exit(1)
    else:
        target_date = datetime.now().date()
    
    # Generate report
    reporter = DailyReporter()
    report_data = reporter.generate_report(target_date)
    
    # Send email if requested
    if args.send_email:
        reporter.send_email_report(report_data)
    
    # Save HTML if requested
    if args.save_html:
        reporter.save_html_report(report_data, args.save_html)


if __name__ == "__main__":
    main()

