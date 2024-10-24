from django.http import FileResponse
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count, Sum, Avg
from .filters import CourseFilter
from .models import User, OfflinePurchase, Transaction, Module, Course, Task, Assessment, Certification, CertificationQuestion, UserCourseProgress
from .serializers import AssessmentListSerializer, CertificationsSerializer, CourseFilterSerializer, CourseListSerializer, CourseTaskModuleSerializer, CourseUpdateSerializer, ModuleListSerializer, ModuleUpdateSerializer, TaskListSerializer, TaskUpdateSerializer, UserCourseProgressSerializer, UserSerializer, OfflinePurchaseSerializer, TransactionOrderSerializer, TransactionCheckOutSerializer, ModuleSerializer, CourseSerializer, TaskSerializer, AssessmentSerializer, CertificationSerializer, CertificationQuestionSerializer
from .methods import calculate_course_progress, encrypt_password, purchasedUser_encode_token, courseSubscribedUser_encode_token, admin_encode_token, visitor_encode_token
from .authentication import PurchasedUserTokenAuthentication, CourseSubscribedUserTokenAuthentication, AdminTokenAuthentication, VisitorTokenAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
import razorpay
from django.core.files.storage import FileSystemStorage
import os
from django.shortcuts import get_object_or_404
import logging
from rest_framework import generics

logger = logging.getLogger(__name__)
UPLOAD_DIR = '/media/'
client = razorpay.Client(auth=("rzp_test_88QnZEgha1Ucxs", "yMHU4vBu66sKyux6DJ7OfKu8"))

class SignInAPIView(APIView):
    def post(self, request):
        try:
            data = request.data
            email = data.get("email")
            password = data.get("password")
            user = User.objects.get(email=email)
            encryptPassword = encrypt_password(password)  # Assuming this is defined elsewhere
            
            if user.password == encryptPassword:
                if user.role == "purchasedUser":
                    token = purchasedUser_encode_token({"id": str(user.id), "role": user.role})
                elif user.role == "CourseSubscribedUser":
                    token = courseSubscribedUser_encode_token({"id": str(user.id), "role": user.role})
                elif user.role == "admin":
                    token = admin_encode_token({"id": str(user.id), "role": user.role})
                elif user.role == "visitor":
                    token = visitor_encode_token({"id": str(user.id), "role": user.role})
                else:
                    return Response(
                        {"message": "Invalid role"}, status=status.HTTP_400_BAD_REQUEST
                    )
                
                refresh = RefreshToken.for_user(user)
                
                return Response(
                    {
                        "token": str(token),
                        "access": str(refresh.access_token),
                        "data": {"user_id":user.id, "subscription":user.subscription},  # Correctly access .data
                        "message": "User logged in successfully",
                    },
                    status=status.HTTP_200_OK,
                )
            return Response(
                {"message": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED
            )

        except User.DoesNotExist:
            return Response(
                {"message": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            logger.error(e)
            return Response({"message": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

#SIGN UP API / CREATE USER API
class SignUpAPIView(APIView):
    def post(self, request, *args, **kwargs):
        data = request.data
        print(data)
        email = data.get('email')
        mobile = data.get('mobile')
        
        if(OfflinePurchase.objects.filter(customer_email=email).exists() or OfflinePurchase.objects.filter(customer_contact_number=mobile).exists()):
            data['subscription'] = True
        else:
            data['subscription'] = False
        serializer = UserSerializer(data=data)
        if serializer.is_valid():
            raw_password = serializer.validated_data.get('password')
            encrypted_password = encrypt_password(raw_password)
            serializer.save(password=encrypted_password)
            return Response({'data': serializer.data, 'message': "User created successfully"}, status=status.HTTP_201_CREATED)
        else:
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk, *args, **kwargs):
        data = request.data
        user = User.objects.get(pk=pk)
        serializer = UserSerializer(user, data=data)
        
        if serializer.is_valid():
            raw_password = serializer.validated_data.get('password')
            encrypted_password = encrypt_password(raw_password)
            serializer.save(password=encrypted_password)
            return Response({'data': serializer.data, 'message': "User updated successfully"})
        else:
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class OrderAPIView(APIView):
    def post(self, request):
        try:
            data = request.data
            user_id = data.get('user_id')
            amount = data.get('amount')
            currency = data.get('currency')
            receipt = data.get('receipt')
            # notes = data.get('notes')
            
            serializedTransaction = TransactionOrderSerializer(data=data)
            if serializedTransaction.is_valid():
                serializedTransaction.save()
                response = client.order.create(data={'amount': amount, 'currency': currency, 'receipt': receipt})
                response['user_id'] = user_id
                return Response({'data': response}, status=status.HTTP_200_OK)
            else:
                return Response({'error': serializedTransaction.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(e)
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class CheckoutAPIView(APIView):
    def post(self, request):
        try:
            data = request.data
            user_id = data.get('user_id')
            razorpay_order_id = data.get('orderId')
            razorpay_payment_id = data.get('paymentId')
            razorpay_signature = data.get('signature')
            print(data)
            serializedTransaction = TransactionCheckOutSerializer(data=data)
            if(serializedTransaction.is_valid()):
                response = client.utility.verify_payment_signature({'razorpay_order_id': razorpay_order_id,'razorpay_payment_id': razorpay_payment_id, 'razorpay_signature': razorpay_signature})
                print(response)
                # Retrieve the Transaction object based on user_id
                transaction = get_object_or_404(Transaction, user_id=user_id)
                print(transaction)
                # Update transaction details
                transaction.razorpay_order_id = razorpay_order_id
                transaction.razorpay_payment_id = razorpay_payment_id
                transaction.razorpay_signature = razorpay_signature
                
                # Save the updated transaction
                transaction.save()
                print(transaction.razorpay_order_id)
                # Save the serialized data
                serializedTransaction.save()
                return Response({'data': {"response":response, "user_id":user_id}}, status=status.HTTP_200_OK)
            else:
                return Response({'error': serializedTransaction.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(e)
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class OfflinePurchaseUserAPIView(APIView):
    def post(self, request):
        try:
            data = request.data
            serializer = OfflinePurchaseSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response({'data': serializer.data, 'message': "Offline purchase created successfully"}, status=status.HTTP_201_CREATED)
            else:
                return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(e)
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    def put(self, request, pk, *args, **kwargs):
        data = request.data
        offline_purchase = OfflinePurchase.objects.get(pk=pk)
        serializer = OfflinePurchaseSerializer(offline_purchase, data=data)
        
        if serializer.is_valid():
            serializer.save()
            return Response({'data': serializer.data, 'message': "Offline purchase updated successfully"})
        else:
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
    def get(self, request, pk, *args, **kwargs):
        offline_purchase = OfflinePurchase.objects.get(pk=pk)
        serializer = OfflinePurchaseSerializer(offline_purchase)
        return Response({'data': serializer.data}, status=status.HTTP_200_OK)
        
    def delete(self, request, pk, *args, **kwargs):
        offline_purchase = OfflinePurchase.objects.get(pk=pk)
        offline_purchase.delete()
        return Response({'message': 'Offline purchase deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
    
class FileRecieverAPIView(APIView):
    UPLOAD_DIR = 'E:/iBOT Ventures/media/'  # Specify your upload directory
    def post(self, request, format=None):
        serializer = ModuleSerializer(data=request.data)

        if serializer.is_valid():
            uploaded_file = request.FILES.get('file')

            # Ensure that the file uploaded is a `.pptx`
            if uploaded_file is None:
                return Response({"error": "No file was uploaded."}, status=status.HTTP_400_BAD_REQUEST)

            if not uploaded_file.name.endswith('.pptx'):
                return Response({"error": "Only .pptx files are allowed."}, status=status.HTTP_400_BAD_REQUEST)

            # Create the upload directory if it does not exist
            if not os.path.exists(self.UPLOAD_DIR):
                os.makedirs(self.UPLOAD_DIR)

            # Generate a new filename based on the module name
            module_name = serializer.validated_data['module_name']
            new_filename = f"{module_name}.pptx"  # Add .pptx extension

            # Ensure unique filename by checking if it exists
            counter = 1
            while os.path.exists(os.path.join(self.UPLOAD_DIR, new_filename)):
                new_filename = f"{module_name}_{counter}.pptx"  # Append a number to make it unique
                counter += 1

            # Save the file to the specified directory
            fs = FileSystemStorage(location=self.UPLOAD_DIR)
            fs.save(new_filename, uploaded_file)

            # Create a Module instance and save it with the new filename
            module_instance = Module(module_name=module_name, file=new_filename)
            module_instance.save()

            return Response({"message": "File uploaded successfully", "file_path": fs.url(new_filename)}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get(self, request, format=None):
        try:
            # List all files in the specified directory
            files = os.listdir(self.UPLOAD_DIR)

            # Filter the list to include only .pptx files
            pptx_files = [file for file in files if file.endswith('.pptx')]

            return Response({"data": pptx_files}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class FileRetrieveAPIView(APIView):
    UPLOAD_DIR = 'E:/iBOT Ventures/media/'  # Specify your upload directory

    def get(self, request, file_name, format=None):
        # Ensure the file name ends with .pptx
        if not file_name.endswith('.pptx'):
            return Response({"error": "Invalid file type. Only .pptx files can be retrieved."}, status=status.HTTP_400_BAD_REQUEST)

        # Create the full file path
        file_path = os.path.join(self.UPLOAD_DIR, file_name)

        # Check if the file exists
        if not os.path.exists(file_path):
            return Response({"error": "File not found."}, status=status.HTTP_404_NOT_FOUND)

        # Return the file as a response
        response = FileResponse(open(file_path, 'rb'), content_type='application/vnd.openxmlformats-officedocument.presentationml.presentation')
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'  # Force download with the original filename
        return response
    
class CourseAPIView(APIView):
    def post(self, request):
        serializer = CourseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"data": serializer.data}, status=status.HTTP_201_CREATED)
        print(serializer.errors)
        logger.error(serializer.errors)
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    def get(self, request):
        try:
            courses = Course.objects.all()
            serializer = CourseListSerializer(courses, many=True)
            return Response({"data": serializer.data}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(e)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
class CourseUpdateAPIView(APIView):
    def put(self, request, pk):
        try:
            course = Course.objects.get(pk=pk)
            serializer = CourseUpdateSerializer(course, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({"data": serializer.data}, status=status.HTTP_200_OK)
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Course.DoesNotExist:
            return Response({"error": "Course not found."}, status=status.HTTP_404_NOT_FOUND)   
        except Exception as e:
            logger.error(e)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TaskAPIView(APIView):
    def get(self, request):
        try:
            course_id = request.query_params.get('course_id', None)
            if course_id:
                tasks = Task.objects.filter(course_id=course_id)
                if tasks.exists():
                    serializer = TaskListSerializer(tasks, many=True)
                    return Response({"data": serializer.data}, status=status.HTTP_200_OK)
                return Response({"error": "No tasks found for the given course."}, status=status.HTTP_404_NOT_FOUND)
        except Task.DoesNotExist:
            return Response({"error": "Task not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        try:
            course_id = request.data.get('course_id')
            course = Course.objects.get(pk=course_id)
            task_name = request.data.get('task_name')
            task_description = request.data.get('task_description')
            task_duration = request.data.get('task_duration')
            serializer = TaskUpdateSerializer(data={'task_name': task_name, 'task_description': task_description, 'task_duration': task_duration})
            if serializer.is_valid():
                serializer.save(course=course)
                return Response({"data": serializer.data}, status=status.HTTP_201_CREATED)
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Course.DoesNotExist:
            return Response({"error": "Course not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class TaskUpdateAPIView(APIView):
    def put(self, request, pk):
        try:
            task = Task.objects.get(pk=pk)
            serializer = TaskUpdateSerializer(task, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({"data": serializer.data}, status=status.HTTP_200_OK)
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Task.DoesNotExist:
            return Response({"error": "Task not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)      
        
class ModuleAPIView(APIView):
    def get(self, request):
        try:
            task_id = request.query_params.get('task_id', None)
            if task_id:
                modules = Module.objects.filter(task_id=task_id)
                if modules.exists():
                    serializer = ModuleListSerializer(modules, many=True)
                    return Response({"data": serializer.data}, status=status.HTTP_200_OK)
            
            return Response({"error": "No modules found for the given task."}, status=status.HTTP_404_NOT_FOUND)
        except Module.DoesNotExist:
            return Response({"error": "Module not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def post(self, request):
        try:
            task_id = request.data.get('task_id')
            task = Task.objects.get(pk=task_id)
            module_name = request.data.get('module_name')
            module_description = request.data.get('module_description')
            module_type = request.data.get('module_type')
            file = request.data.get('file')
            serializer = ModuleListSerializer(data={'module_name': module_name, 'module_description': module_description, 'module_type': module_type, 'file': file})
            if serializer.is_valid():
                serializer.save(task=task)
                return Response({"data": serializer.data}, status=status.HTTP_201_CREATED)
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Task.DoesNotExist:
            return Response({"error": "Task not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class ModuleUpdateAPIView(APIView):        
    def put(self, request, pk):
        try:
            module = Module.objects.get(pk=pk)
            serializer = ModuleUpdateSerializer(module, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({"data": serializer.data}, status=status.HTTP_200_OK)
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Module.DoesNotExist:
            return Response({"error": "Module not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
class AssessmentAPIView(APIView):
    def get(self, request):
        try:
            module_id = request.query_params.get('module_id', None)
            if module_id:
                assessments = Assessment.objects.filter(module_id=module_id)
                if assessments.exists():
                    serializer = AssessmentListSerializer(assessments, many=True)
                    return Response({"data": serializer.data}, status=status.HTTP_200_OK)
                return Response({"error": "No assessments found for the given module."}, status=status.HTTP_404_NOT_FOUND)
        except Assessment.DoesNotExist:
            return Response({"error": "Assessment not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def post(self, request):
        module_id = request.data.get('module_id')
        
        if module_id is None:
            return Response({"error": "module_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            module = Module.objects.get(id=module_id)
        except Module.DoesNotExist:
            return Response({"error": "Module not found"}, status=status.HTTP_404_NOT_FOUND)

        data = {
            'question': request.data.get('question'),
            'option1': request.data.get('option1'),
            'option2': request.data.get('option2'),
            'option3': request.data.get('option3'),
            'option4': request.data.get('option4'),
            'answer': request.data.get('answer'),
            'module': module.id
        }

        serializer = AssessmentSerializer(data=data)
        if serializer.is_valid():
            serializer.save(module=module)  # Save the assessment with the linked module
            return Response({"data": serializer.data}, status=status.HTTP_201_CREATED)
        else:
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
class AssessmentUpdateAPIView(APIView):
    def put(self, request, pk):
        try:
            assessment = Assessment.objects.get(pk=pk)
            serializer = AssessmentSerializer(assessment, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({"data": serializer.data}, status=status.HTTP_200_OK)
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Assessment.DoesNotExist:
            return Response({"error": "Assessment not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
class CertificationAPIView(APIView):
    def get(self, request, *args, **kwargs):
        course_id = request.query_params.get('course_id', None)
        if course_id:
            certifications = Certification.objects.filter(course_id=course_id)
            serializer = CertificationsSerializer(certifications, many=True)
            return Response({"data": serializer.data}, status=status.HTTP_200_OK)
        return Response({"error": "Course ID is required."}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, *args, **kwargs):
        print(request.data)
    
        course_id = request.data.get('course_id')
        certification_data = request.data.get('certification')
        
        if not course_id:
            return Response({"error": "Course ID is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not certification_data:
            return Response({"error": "Certification data is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Fetch the course by ID
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({"error": "Course not found."}, status=status.HTTP_404_NOT_FOUND)
        
        print(course)
        # Prepare data for certification creation
        certification_data['course'] = course.id  # Associate course with certification

        # Serialize the certification data and pass the course in context
        serializer = CertificationsSerializer(data=certification_data, context={'course': course})
        
        if serializer.is_valid():
            # Save the certification and related questions
            serializer.save()
            return Response({"data": serializer.data}, status=status.HTTP_201_CREATED)
        
        logger.error(serializer.errors)
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class CertificationUpdateAPIView(APIView):
    def put(self, request, pk):
        try:
            certification = Certification.objects.get(pk=pk)
            serializer = CertificationSerializer(certification, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({"data": serializer.data}, status=status.HTTP_200_OK)
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Certification.DoesNotExist:
            return Response({"error": "Certification not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class UserCourseProgressView(APIView):
    def get(self, request):
        try:
            user = request.query_params.get('user_id')
            course_id = request.query_params.get('course_id')
            course = Course.objects.get(id=course_id)
            progress = UserCourseProgress.objects.get(user=user, course=course)
            serializer = UserCourseProgressSerializer(progress)
            progressPercent = calculate_course_progress(user, course)
            data = {'progress': progressPercent, 'data': serializer.data}
            return Response({"data": data}, status=status.HTTP_200_OK)
        except UserCourseProgress.DoesNotExist:
            return Response({"detail": "Progress not found for the specified course."}, status=status.HTTP_404_NOT_FOUND)
        except Course.DoesNotExist:
            return Response({"detail": "Course not found."}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        user_id = request.data.get('user_id')
        course_id = request.data.get('course_id')
        
        user = User.objects.get(id=user_id)
        
        if not user:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        elif not course_id:
            return Response({"detail": "Course ID is required."}, status=status.HTTP_400_BAD_REQUEST)
        elif user.subscription == False:
            return Response({"detail": "User has not subscribed to the course."}, status=status.HTTP_400_BAD_REQUEST)
        
        else:
            course = Course.objects.get(id=course_id)

            try:
                progress = UserCourseProgress.objects.get(user=user, course=course)
            except UserCourseProgress.DoesNotExist:
                progress = UserCourseProgress(user=user, course=course)

            last_module_id = request.data.get('last_module')
            last_task_id = request.data.get('last_task')
            is_completed = request.data.get('is_completed', False)

            if last_module_id:
                try:
                    last_module = Module.objects.get(id=last_module_id)
                    progress.last_module = last_module
                except Module.DoesNotExist:
                    return Response({"detail": "Module not found."}, status=status.HTTP_404_NOT_FOUND)

            if last_task_id:
                try:
                    last_task = Task.objects.get(id=last_task_id)
                    progress.last_task = last_task
                except Task.DoesNotExist:
                    return Response({"detail": "Task not found."}, status=status.HTTP_404_NOT_FOUND)

            progress.is_completed = is_completed
            progress.save()

            serializer = UserCourseProgressSerializer(progress)
            return Response({"data": serializer.data}, status=status.HTTP_200_OK)

class UserCourseProgressUpdateView(APIView):
    def put(self, request, pk):
        try:
            user_course_progress = UserCourseProgress.objects.get(pk=pk)
        except UserCourseProgress.DoesNotExist:
            return Response({"error": "User course progress not found"}, status=status.HTTP_404_NOT_FOUND)

        user_id = request.data.get('user_id')
        course_id = request.data.get('course_id')

        if user_id is None or course_id is None:
            return Response({"error": "user_id and course_id are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_id = str(user_id) 
            course_id = str(course_id)
        except (ValueError, TypeError):
            return Response({"error": "Invalid user_id or course_id"}, status=status.HTTP_400_BAD_REQUEST)

        if (str(user_course_progress.user.id) == user_id) and (str(user_course_progress.course.id) == course_id):
            last_module_id = request.data.get('last_module')
            last_task_id = request.data.get('last_task')
            is_completed = request.data.get('is_completed', False)

            if last_module_id:
                try:
                    last_module = Module.objects.get(id=last_module_id)
                    user_course_progress.last_module = last_module
                except Module.DoesNotExist:
                    return Response({"error": "Last module not found"}, status=status.HTTP_404_NOT_FOUND)

            if last_task_id:
                try:
                    last_task = Task.objects.get(id=last_task_id)
                    user_course_progress.last_task = last_task
                except Task.DoesNotExist:
                    return Response({"error": "Last task not found"}, status=status.HTTP_404_NOT_FOUND)

            user_course_progress.is_completed = is_completed
            user_course_progress.save()

            return Response({"data": UserCourseProgressSerializer(user_course_progress).data}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "User course progress does not match the provided user_id and course_id"}, status=status.HTTP_400_BAD_REQUEST)

class CourseTaskModuleCountAPIView(APIView):
    def get(self, request):
        try:
            course_id = request.query_params.get('course_id')   
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = CourseTaskModuleSerializer(course)
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)
    
class CourseListView(APIView):
    def get(self, request, *args, **kwargs):
        queryset = Course.objects.all()
        filterset = CourseFilter(request.GET, queryset=queryset)
        
        if filterset.is_valid():
            queryset = filterset.qs  # Get the filtered queryset
        serializer = CourseFilterSerializer(queryset, many=True)
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)
    
class StatisticsAPIView(APIView):
    
    def get(self, request):
        # User statistics
        total_users = User.objects.count()
        purchased_users = User.objects.filter(role='purchasedUser').count()
        subscribed_users = User.objects.filter(subscription=True).count()
        users_by_role = User.objects.values('role').annotate(count=Count('role'))

        # Offline Purchase statistics
        total_purchases = OfflinePurchase.objects.count()
        purchases_by_product = OfflinePurchase.objects.values('product_name').annotate(count=Count('product_name'))
        revenue_by_product = OfflinePurchase.objects.values('product_name').annotate(revenue=Sum('product_price'))
        purchases_by_payment_method = OfflinePurchase.objects.values('payment_term').annotate(count=Count('payment_term'))

        # Course statistics
        total_courses = Course.objects.count()
        courses_by_level = Course.objects.values('level').annotate(count=Count('level'))
        courses_by_age_category = Course.objects.values('age_category').annotate(count=Count('age_category'))
        courses_by_product = Course.objects.values('product_model').annotate(count=Count('product_model'))

        # Preparing data for the serializer
        data = {
            'total_users': total_users,
            'purchased_users': purchased_users,
            'subscribed_users': subscribed_users,
            'users_by_role': {item['role']: item['count'] for item in users_by_role},

            'total_purchases': total_purchases,
            'purchases_by_product': {item['product_name']: item['count'] for item in purchases_by_product},
            'revenue_by_product': {item['product_name']: item['revenue'] for item in revenue_by_product},
            'purchases_by_payment_method': {item['payment_term']: item['count'] for item in purchases_by_payment_method},

            'total_courses': total_courses,
            'courses_by_level': {item['level']: item['count'] for item in courses_by_level},
            'courses_by_age_category': {item['age_category']: item['count'] for item in courses_by_age_category},
            'courses_by_product': {item['product_model']: item['count'] for item in courses_by_product},
        }
        
        return Response({"data": data}, status=status.HTTP_200_OK)