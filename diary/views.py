from rest_framework.response import Response
from rest_framework import status
from .models import Diary, DiaryImg, Emotion, Weather
from account.models import User
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .serializers import BaseDiarySerializer, DiaryListsSerializer
import itertools
from operator import itemgetter
import boto3
from .services import send_img_create_req, send_summary_req
import backend.config.settings.base as settings
from botocore.client import Config


# S3
import boto3

## env
from django.conf import settings



@ensure_csrf_cookie
@api_view(('GET',))
@permission_classes([IsAuthenticated])
def diary_lists(request):
    if (request.method == 'GET'):
        try:
            user = request.user
            user_id = user.user_id
            res_data_raw = Diary.objects.filter(user_id = user_id) \
                .extra(select={'year_month': "DATE_FORMAT(date, '%%Y-%%m')", 'year_month_date': "DATE_FORMAT(date, '%%Y-%%m-%%d')"}) \
                .values('year_month', 'diary_id', 'image_url').order_by('-year_month_date')

            serializer = DiaryListsSerializer(res_data_raw, many=True)
            res_data_json = serializer.data
            sorted_data = sorted(res_data_json, key=itemgetter('year_month'), reverse=True)
 
            grouped_data = itertools.groupby(sorted_data, key=itemgetter('year_month'))
            res = {}
            for key, group_data in grouped_data:
                res[key] = list(group_data)
              
            return Response({'message' : '조회에 성공하였습니다.', 'data' : res}, status=status.HTTP_200_OK)
            
        except:
            return Response({'err_msg' : '서버 오류입니다.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@ensure_csrf_cookie
@api_view(('POST',))
@permission_classes([IsAuthenticated])
def diary_create(request):
    if (request.method == 'POST'):
        try:
            user = request.user
            user_id = user.user_id
            date = request.data['date']
            content = request.data['content']
            wea_id = request.data['wea_id']
            emo_id = request.data['emo_id']
            user = User.objects.get(user_id=user_id)
            emo = Emotion.objects.get(emo_id=emo_id)
            wea = Weather.objects.get(wea_id=wea_id)
            diary = Diary.objects.create(date=date, content=content, emo_id=emo, wea_id=wea, user_id=user)
                
            # ml 서버로 request 전송, 응답으로 prompt 받음
            prompt = send_summary_req(content)
            DiaryImg.objects.create(prompt=prompt, diary_id=diary)

            return Response({'message' : '일기 저장을 성공하였습니다.', 'diary_id' : diary.diary_id, 'prompt': prompt}, status=status.HTTP_200_OK)
            
        except:
            return Response({'err_msg' : '서버 오류입니다.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@ensure_csrf_cookie
@api_view(('GET',))
@permission_classes([IsAuthenticated])
def diary_one(request, diaryId):
    if(request.method == 'GET'):
        try:
            diary_id = diaryId
            diary = Diary.objects.filter(diary_id=diary_id).values('diary_id', 'date', 'content', 'emo_id', 'wea_id', 'image_url')
            serializer = BaseDiarySerializer(diary, many=True)                    
            res = serializer.data
            
            return Response({'message' : '일기 조회를 성공하였습니다.', 'res':res}, status=status.HTTP_200_OK)
        
        except Diary.DoesNotExist:
            return Response({'err_msg' : '존재하지 않는 일기입니다.'}, status=status.HTTP_400_BAD_REQUEST)
        except:
            return Response({'err_msg' : '서버 오류입니다.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)        
                
            
                
@ensure_csrf_cookie
@api_view(('PATCH',))
@permission_classes([IsAuthenticated])
def diary_update(request):
    if (request.method == 'PATCH'):
        try:
            diary_id = request.GET['id']            
            diary = Diary.objects.get(diary_id=diary_id)
            
            print(request.data)
            new_content = diary.content if request.data['new_content'] == '' else request.data['new_content']
            new_wea = diary.wea_id if request.data['new_wea'] == '' else Weather.objects.get(wea_id=request.data['new_wea'])
            new_emo = diary.emo_id if request.data['new_emo'] == '' else Emotion.objects.get(emo_id=request.data['new_emo'])
            new_date = diary.date if request.data['new_date'] == '' else request.data['new_date']
            
            diary.content = new_content
            diary.wea_id = new_wea
            diary.emo_id = new_emo
            diary.date = new_date
            diary.save()

            return Response({'message' : '일기 수정을 성공하였습니다.', 'diary_id' : diary.diary_id}, status=status.HTTP_200_OK)
        
        except Diary.DoesNotExist:
            return Response({'err_msg' : '존재하지 않는 일기입니다.'}, status=status.HTTP_400_BAD_REQUEST)
        except KeyError:
            return Response({'err_msg' : 'KeyError: \'new_content\''}, status=status.HTTP_400_BAD_REQUEST)
        except:
            return Response({'err_msg' : '서버 오류입니다.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@ensure_csrf_cookie
@api_view(('PATCH',))
@permission_classes([IsAuthenticated])
def create_img(request):
    if (request.method == 'PATCH'):
        try:
            diary_id = request.GET['id']
            diary = Diary.objects.get(diary_id=diary_id)
            diary_img = DiaryImg.objects.get(diary_id=diary)
            prompt = diary_img.prompt
            print(prompt)
            url = send_img_create_req(prompt)
            
            diary.image_url = url
            diary.save()
            print(diary)
            
            diary_img.url = url
            diary_img.save()
       
            return Response({'message' : '그림 생성을 성공하였습니다.', 'url' : url}, status=status.HTTP_200_OK)
        
        except Diary.DoesNotExist:
            return Response({'err_msg' : '존재하지 않는 일기입니다.'}, status=status.HTTP_400_BAD_REQUEST)
        except:
            return Response({'err_msg' : '서버 오류입니다.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@ensure_csrf_cookie
@api_view(('DELETE',))   
@permission_classes([IsAuthenticated])     
def diary_del(request):
    if (request.method == 'DELETE'):
        try:
            diary_id = request.GET['id']
            target_diary = Diary.objects.get(diary_id=diary_id)
            target_diary.delete()
            
            return Response({'message' : '일기 삭제를 성공하였습니다.'}, status=status.HTTP_200_OK)
            
        except:
            return Response({'err_msg' : '서버 오류입니다.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
    
@ensure_csrf_cookie
@api_view(('GET',))
@permission_classes([IsAuthenticated])    
def get_s3_presigned_url(request):
    if (request.method == 'PUT'):
        AWS_ACCESS_KEY_ID_2 = getattr(settings, 'AWS_ACCESS_KEY_ID_2', 'AWS_ACCESS_KEY_ID_2')
        AWS_SECRET_ACCESS_KEY_2 = getattr(settings, 'AWS_SECRET_ACCESS_KEY_2', 'AWS_SECRET_ACCESS_KEY_2')
        AWS_STORAGE_BUCKET_NAME = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'AWS_STORAGE_BUCKET_NAME')
        AWS_REGION = getattr(settings, 'AWS_REGION', 'AWS_REGION')
        AWS_S3_CUSTOM_DOMAIN = getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', 'AWS_S3_CUSTOM_DOMAIN')

        client = boto3.client('s3',
                           aws_access_key_id=AWS_ACCESS_KEY_ID_2,
                           aws_secret_access_key=AWS_SECRET_ACCESS_KEY_2,
                           region_name=AWS_REGION)
        print(client)
        s3 = boto3.resource('s3', config=Config(signature_version="s3v4"))
        buckets = s3.Bucket(name=AWS_STORAGE_BUCKET_NAME)
        print(buckets)
        
        # presigned URL 생성
        url = client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': AWS_STORAGE_BUCKET_NAME,
                'Key': 'test.txt',
            },
            # url 생성 후 10초가 지나면 접근 불가
            ExpiresIn=3600
        )
        
        # 이미지 파일 업로드
        # s3 = boto3.resource('s3')
        # s3.Object(AWS_STORAGE_BUCKET_NAME, 'image.jpg').upload_fileobj(image_file)
        
        print(url)
    
    return Response({'s3_url' : url})



#######################################################################

from .services import send_img

@ensure_csrf_cookie
@api_view(('POST',))
@permission_classes([IsAuthenticated])
def diary_uploadImg(request):
    if (request.method == 'POST'):
        try:
            user = request.user
            user_id = user.user_id
            date = request.data['date']
            #content = request.data['content']
            wea_id = request.data['wea_id']
            emo_id = request.data['emo_id']
            user = User.objects.get(user_id=user_id)
            emo = Emotion.objects.get(emo_id=emo_id)
            wea = Weather.objects.get(wea_id=wea_id)
            diary = Diary.objects.create(date=date, emo_id=emo, wea_id=wea, user_id=user)
                

            # 이미지 파일 받기
            image_file = request.FILES.get('image')
            if image_file is None:
                return Response({'error': '이미지 파일이 존재하지 않습니다.'}, status=status.HTTP_400_BAD_REQUEST)

            # presigned URL에 이미지 저장
            # print("presigned URL에 이미지 저장 전:", image_file) ### debug
            url = send_img(image_file)
            # print("presigned URL에 이미지 저장 후:", url)        ### debug
            
            prompt = send_img(url)
            DiaryImg.objects.create(prompt=prompt, diary_id=diary)

            
            return Response({'message' : '대화 이미지로 일기 저장을 성공하였습니다.', 'diary_id' : diary.diary_id, 'prompt':prompt}, status=status.HTTP_200_OK)

        except:
            return Response({'err_msg': '대화 이미지로 일기를 저장하는데 실패했습니다.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
