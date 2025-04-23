import logging
from .models import ScheduledTaskLog
from django.utils import timezone
from ECHOME.BLOCK_CHAIN import ChainContract
from ECHOME.IPFS import FilebaseIPFS
from ECHOME.SMTP import send_email_with_attachment
from ECHOME.models import TimeCapsule
from .utility_functions import utility_functions
from django_apscheduler import util
from datetime import timedelta
from django.utils.timezone import now



logger = logging.getLogger(__name__)

@util.close_old_connections
def send_notification():
    """
    main task that notifies users about their expired time capsule
    and send them the file

    """
    log_entry = ScheduledTaskLog.objects.create(
        task_name="send_notification",
        status="running"
    )

    try:

        logger.info("Executing notification  task")

        contract = ChainContract() #contract object
        print("contract initialized")

        ipfsClient = FilebaseIPFS()  # filebase object

        list_cid = contract.get_expired_data()

        print("list of cid",list_cid)

        if not list_cid:
            logger.info("No expired CIDs found")
            log_entry.status = "completed"
            log_entry.details = "No expired CIDs found"
            return

        else:
            for cid in list_cid:
                try:
                    print("for cid",cid)

                    capsules = TimeCapsule.objects.filter(cid=cid[-12:])
                    if capsules.count() == 1:
                        capsule = capsules[0]
                    else:
                        current_time = now()
                        capsule = None
                        smallest_diff = None

                        for record in capsules:
                            time = record.storage_time + timedelta(seconds=record.unlock_time)
                            diff = abs((time - current_time).total_seconds())

                            if smallest_diff is None or diff < smallest_diff:
                                smallest_diff = diff
                                capsule = record

                    data = {
                        'cid': cid,
                        'email': capsule.email,
                        'decryption_pass': capsule.decryption_pass,
                        'storage_time': capsule.storage_time
                    }

                except TimeCapsule.DoesNotExist:
                    print("capsule dta in db  not found")
                    logger.error(f"Time capsule with CID {cid} not found.")
                    ipfsClient.delete_file_by_cid(cid)
                    continue

                '''get file from ipfs and check it '''

                print("getting file from ipfs")
                file_dict = ipfsClient.get_file_by_cid(cid)

                if not file_dict:
                    logger.error(f"Failed to retrieve file for CID {cid}")
                    print("file not found in filebase")
                    capsule.status = "failed"
                    capsule.save()
                    continue

                logger.info(f"File retrieved successfully for CID {cid}")


                ''' initialising  utility class '''

                utility_client = utility_functions()


                ''''check if file is encrypted or not '''

                decrypted_file = utility_client.decrypt_aes256_cbc(file_dict["bytes"], data['decryption_pass'])
                print("decrypted file")
                if not decrypted_file:
                    logger.error(f"Decryption failed for CID {cid}")
                    capsule.status = "failed"
                    capsule.save()
                    continue
                '''file type and extension '''
                #
                ext_and_mime=utility_client.get_file_type(decrypted_file)

                file_dict['mime_type'] = ext_and_mime[0]
                file_dict['ext'] = ext_and_mime[1]
                print("file type and extension", file_dict['mime_type'], file_dict['ext'])

                '''send email with decrypted file '''
                print("email sending")

                diffrance = utility_client.detailed_time_difference(data['storage_time'])

                email_sent = send_email_with_attachment(
                    to_email=data['email'],
                    file_info=file_dict,
                    time=data['storage_time'],
                    time_diffrance=diffrance,
                )
                print("email sent")
                if not email_sent:
                    logger.error(f"Failed to send email for CID {cid}")
                    capsule.status = "failed"
                    capsule.save()
                    continue
                else:
                    logger.info(f"Email sent successfully for CID {cid}")
                    capsule.status = "sent"
                    capsule.save()

            log_entry.status = "completed"

        log_entry.details = "Task completed successfully"

    except Exception as e:
        logger.error(f"Task failed: {str(e)}")
        log_entry.status = "failed"
        log_entry.details = str(e)
        print("error", e)
    finally:
        log_entry.completed_at = timezone.now()
        log_entry.save()

def cleanup_old_logs(days_to_keep=7):
    """
    Cleans up old task logs
    """
    from django.utils import timezone
    from datetime import timedelta

    cutoff_date = timezone.now() - timedelta(days=days_to_keep)
    deleted_count, _ = ScheduledTaskLog.objects.filter(
        started_at__lt=cutoff_date
    ).delete()

    logger.info(f"Deleted {deleted_count} old log entries")