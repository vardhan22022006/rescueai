"""
Background scheduler for RescueAI.

Runs periodic tasks:
- Re-score active reports every 5 minutes (applies time decay)
- Can be extended for other maintenance tasks

Uses APScheduler for reliable background job execution.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import atexit

from app.database import SessionLocal
from app.pipeline.scoring import rescore_all_active_reports


# Global scheduler instance
scheduler = None


def rescore_job():
    """
    Periodic job to re-score all active reports.
    
    Applies time decay to reports that haven't been updated.
    Runs every 5 minutes.
    """
    print(f"\n[{datetime.utcnow().isoformat()}] Starting periodic rescoring job...")
    
    db = SessionLocal()
    
    try:
        results = rescore_all_active_reports(db)
        
        print(f"  ✓ Rescored {results['total_rescored']} active reports")
        print(f"    - {results['scores_increased']} increased")
        print(f"    - {results['scores_decreased']} decreased")
        print(f"    - {results['scores_unchanged']} unchanged")
        
        # Log significant changes
        if results['details']:
            print(f"  Significant changes (±5 points):")
            for detail in results['details'][:5]:  # Show top 5
                change_dir = "↑" if detail['change'] > 0 else "↓"
                print(f"    {change_dir} Report {detail['report_id'][:8]}: "
                      f"{detail['old_score']:.0f} → {detail['new_score']:.0f} "
                      f"({detail['change']:+.0f})")
        
        print(f"  Job completed successfully\n")
        
    except Exception as e:
        print(f"  ✗ Error during rescoring: {e}\n")
    finally:
        db.close()


def start_scheduler():
    """
    Start the background scheduler.
    
    Called when the application starts.
    Scheduler runs in a separate thread.
    """
    global scheduler
    
    if scheduler is not None:
        print("Scheduler already running")
        return
    
    print("\n=== Starting RescueAI Background Scheduler ===")
    
    scheduler = BackgroundScheduler()
    
    # Job 1: Re-score active reports every 5 minutes
    scheduler.add_job(
        func=rescore_job,
        trigger=IntervalTrigger(minutes=5),
        id='rescore_active_reports',
        name='Re-score active reports (time decay)',
        replace_existing=True,
        max_instances=1  # Prevent overlapping runs
    )
    
    # Start the scheduler
    scheduler.start()
    
    print("✓ Scheduler started")
    print("  Jobs:")
    print("    - Re-score active reports: every 5 minutes")
    print("=" * 48 + "\n")
    
    # Shut down scheduler when app exits
    atexit.register(lambda: shutdown_scheduler())


def shutdown_scheduler():
    """
    Shut down the background scheduler gracefully.
    
    Called when the application stops.
    """
    global scheduler
    
    if scheduler is not None:
        print("\n=== Shutting down RescueAI Scheduler ===")
        scheduler.shutdown(wait=True)
        scheduler = None
        print("✓ Scheduler stopped\n")


def run_rescore_now():
    """
    Manually trigger a rescoring job immediately.
    
    Useful for:
    - Testing
    - Manual maintenance
    - After bulk data imports
    
    Returns:
        Results from rescore_all_active_reports
    """
    print("\nManually triggering rescoring job...")
    
    db = SessionLocal()
    
    try:
        results = rescore_all_active_reports(db)
        print(f"✓ Rescored {results['total_rescored']} reports")
        return results
    finally:
        db.close()


def get_scheduler_status() -> dict:
    """
    Get current scheduler status and job information.
    
    Returns:
        Dict with scheduler state and job details
    """
    global scheduler
    
    if scheduler is None:
        return {
            'running': False,
            'jobs': []
        }
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
            'trigger': str(job.trigger)
        })
    
    return {
        'running': True,
        'jobs': jobs,
        'state': str(scheduler.state)
    }
