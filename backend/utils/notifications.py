from plyer import notification
import time


def notify_user(title, message, duration=5):
    """Send a system notification to the user."""
    notification.notify(
        title=title,
        message=message,
        app_name="Outreach Assistant",
        timeout=duration,
        toast=True,
    )
    # Small delay to ensure notification is shown
    time.sleep(0.1)
