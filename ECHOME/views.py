from django.http import JsonResponse
from .models import TimeCapsule
from .IPFS import FilebaseIPFS
from .BLOCK_CHAIN import ChainContract
from django.core.exceptions import ValidationError
# from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render


def homepage(request):
    return render(request, 'index.html')

def formpage(request):
    return render(request, 'form.html')

def signuppage(request):
    return render(request, 'signup.html')


def process_secure_upload(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)

    try:
        # Get the uploaded file object
        uploaded_file = request.FILES.get('encrypted_file')
        if not uploaded_file:
            raise ValidationError("No file was uploaded")
        else:
            '''
            
            storing file to ipfs to get cid 
            
            '''
            ipfs = FilebaseIPFS()  # Initialize IPFS client
            cid = ipfs.upload_and_get_cid(uploaded_file)  # upload file to IPFS and get CID

        # Get form data
        unlock_time = int(request.POST.get('unlock_time'))
        email = request.POST.get('email')
        decryption_password = request.POST.get('password')

        if not all([unlock_time, email, decryption_password]):
            raise ValidationError("All fields (unlock_time, email, password) are required")
        print("got all data ")

        '''
        
        storing cid and to sepoliaetherium  via smart contracts 
         
         '''
        try:
            print("storing to blockchain")
            contract = ChainContract()  # Initialize the contract
            contract.store_data(cid,unlock_time)
        except Exception as e:
            print("failed to store to blockchain")
            ipfs.delete_file_by_cid(cid)
            raise ValidationError("Failed to store data on the blockchain") from e

        '''
        storing to mysql database 

        '''
        TimeCapsule.objects.create(
            email=email,
            cid=cid[-12:],
            decryption_pass=decryption_password,
            unlock_time=unlock_time
        )

        return JsonResponse("stored successfully", safe=False, status=200)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)