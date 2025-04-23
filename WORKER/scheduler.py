from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
def initialize_scheduler():
    from django_apscheduler.jobstores import DjangoJobStore  # Import here
    scheduler.add_jobstore(DjangoJobStore(), "default")