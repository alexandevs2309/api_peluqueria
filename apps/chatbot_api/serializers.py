from rest_framework import serializers


class ChatPromptSerializer(serializers.Serializer):
    prompt = serializers.CharField(
        max_length=1000, 
        required=True, 
        allow_blank=False,
        error_messages={
            'required': 'El campo prompt es obligatorio.',
            'blank': 'El prompt no puede estar vacío.'
        }
    )
