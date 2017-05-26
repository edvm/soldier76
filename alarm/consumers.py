"""Mordor channel consumers."""

import logging

from channels.auth import channel_session_user, channel_session_user_from_http
from base64 import b64decode
from alarm import events
from alarm.channels import get_alarm_group
from alarm.models import (
    Alarm,
    AlarmImage
)
from vision.cloud import azure

logger = logging.getLogger('alarm')


@channel_session_user_from_http
def ws_auth(message):
    """Add user to its group alarm."""
    if not message.user or message.user.is_anonymous:
        logger.debug('Invalid user %s', message.user)
        return
    group = get_alarm_group(message.user)
    group.add(message.reply_channel)
    logger.debug('User %s added to group %s', message.user, group.name)


# Connected to websocket.disconnect
@channel_session_user
def ws_disconnect(message):
    """When user disconnects, remove its group name."""
    group = get_alarm_group(message.user)
    group.discard(message.reply_channel)
    logger.debug('User %s removed from %s', message.user, group.name)


def ws_echo(message):
    """Echo WSGI messages."""
    message.reply_channel.send({
        "text": message.content['text'],
    })


def handle_image(payload):
    """Handle images."""
    encoded_image = payload['encoded_image']  # encoded in base64
    filetype = payload['filetype']
    username = payload['username']
    sender = payload['sender']
    logger.debug('Received image from %s', sender)

    alarm = Alarm.get_by_username(username)
    alarm_image = AlarmImage.create_from_encoded_data(encoded_image, filetype, alarm)

    if alarm.active:
        Alarm.notify(
            Event=events.MotionDetected,
            sender=sender,
            username=username,
            filetype=filetype,
            image_url=alarm_image.full_url,
        )


def get_image_tags(payload):
    """Return tags from given image."""
    encoded_image = payload['encoded_image']  # encoded in base64
    image = b64decode(encoded_image)
    tags = azure.get_image_tags(image)
    return tags
