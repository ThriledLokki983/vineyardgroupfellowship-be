"""
Management command to recalculate comment counts for all content types.
"""
from django.core.management.base import BaseCommand
from django.db.models import Count
from messaging.models import Discussion, Scripture, PrayerRequest, Testimony, Comment
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = 'Recalculate comment counts for all content types'

    def handle(self, *args, **options):
        self.stdout.write('Recalculating comment counts...\n')

        # Scripture
        self.stdout.write('Processing Scripture...')
        scripture_ct = ContentType.objects.get_for_model(Scripture)
        for scripture in Scripture.objects.all():
            count = Comment.objects.filter(
                content_type=scripture_ct,
                content_id=scripture.id,
                is_deleted=False
            ).count()
            if scripture.comment_count != count:
                scripture.comment_count = count
                scripture.save(update_fields=['comment_count'])
                self.stdout.write(
                    f'  Updated {scripture.reference}: {count} comments')

        # PrayerRequest
        self.stdout.write('\nProcessing PrayerRequest...')
        prayer_ct = ContentType.objects.get_for_model(PrayerRequest)
        for prayer in PrayerRequest.objects.all():
            count = Comment.objects.filter(
                content_type=prayer_ct,
                content_id=prayer.id,
                is_deleted=False
            ).count()
            if prayer.comment_count != count:
                prayer.comment_count = count
                prayer.save(update_fields=['comment_count'])
                self.stdout.write(
                    f'  Updated {prayer.title}: {count} comments')

        # Testimony
        self.stdout.write('\nProcessing Testimony...')
        testimony_ct = ContentType.objects.get_for_model(Testimony)
        for testimony in Testimony.objects.all():
            count = Comment.objects.filter(
                content_type=testimony_ct,
                content_id=testimony.id,
                is_deleted=False
            ).count()
            if testimony.comment_count != count:
                testimony.comment_count = count
                testimony.save(update_fields=['comment_count'])
                self.stdout.write(
                    f'  Updated {testimony.title}: {count} comments')

        # Discussion (for completeness)
        self.stdout.write('\nProcessing Discussion...')
        for discussion in Discussion.objects.all():
            count = discussion.comments.filter(is_deleted=False).count()
            if discussion.comment_count != count:
                discussion.comment_count = count
                discussion.save(update_fields=['comment_count'])
                self.stdout.write(
                    f'  Updated {discussion.title}: {count} comments')

        self.stdout.write(self.style.SUCCESS(
            '\n✅ Comment counts recalculated successfully!'))
