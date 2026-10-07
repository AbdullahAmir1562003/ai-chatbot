import os
import json
from groq import Groq
from django.shortcuts import render
from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Conversation, Message
from .serializers import ConversationSerializer

def index(request):
    return render(request, 'index.html')

class ConversationListCreateView(APIView):
    def get(self, request):
        conversations = Conversation.objects.all()
        serializer = ConversationSerializer(conversations, many=True)
        return Response(serializer.data)

    def post(self, request):
        title = request.data.get('title', 'New Chat')
        conversation = Conversation.objects.create(title=title)
        serializer = ConversationSerializer(conversation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class ConversationDetailView(APIView):
    def get(self, request, pk):
        try:
            conversation = Conversation.objects.get(pk=pk)
        except Conversation.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ConversationSerializer(conversation)
        return Response(serializer.data)

    def delete(self, request, pk):
        try:
            conversation = Conversation.objects.get(pk=pk)
            conversation.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Conversation.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

class SendMessageView(APIView):
    def post(self, request, conversation_id):
        try:
            conversation = Conversation.objects.get(pk=conversation_id)
        except Conversation.DoesNotExist:
            return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)

        user_content = request.data.get('message', '').strip()
        if not user_content:
            return Response({'error': 'Message content required'}, status=status.HTTP_400_BAD_REQUEST)

        Message.objects.create(conversation=conversation, role='user', content=user_content)

        if conversation.messages.count() == 1:
            conversation.title = user_content[:40] + ('...' if len(user_content) > 40 else '')
            conversation.save()

        messages_payload = [{"role": "system", "content": "You are a professional, intelligent AI assistant. Provide accurate, structured, and helpful responses."}]
        for msg in conversation.messages.all():
            messages_payload.append({"role": msg.role, "content": msg.content})

        # Insert your real key inside the quotes below:
        api_key = "YOUR_GROQ_API_KEY_HERE"
        def stream_generator():
            full_response = []
            if groq_api_key and groq_api_key.startswith("gsk_"):
                try:
                    client = Groq(api_key=groq_api_key.strip())
                    completion = client.chat.completions.create(
                        model="openai/gpt-oss-120b",
                        messages=messages_payload,
                        stream=True,
                    )
                    for chunk in completion:
                        delta = chunk.choices[0].delta.content or ""
                        full_response.append(delta)
                        yield f"data: {json.dumps({'chunk': delta})}\n\n"
                except Exception as e:
                    err_msg = f"AI Error: {str(e)}"
                    full_response.append(err_msg)
                    yield f"data: {json.dumps({'chunk': err_msg})}\n\n"
            else:
                err_msg = "Please paste your valid Groq API key into views.py."
                full_response.append(err_msg)
                yield f"data: {json.dumps({'chunk': err_msg})}\n\n"

            Message.objects.create(conversation=conversation, role='assistant', content="".join(full_response))
            yield f"data: [DONE]\n\n"

        response = StreamingHttpResponse(stream_generator(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        return response