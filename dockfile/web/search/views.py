from django.shortcuts import render
from django.http import HttpResponseRedirect, Http404
from .models import Member
import redis
import json
# Create your views here.

def read_Member(request):
    member_dict = []
    r = redis.StrictRedis(host='10.113.99.60', port=6379, db=1, charset="utf-8", decode_responses=True)
    print(r)
    data_dict={}
    result = dict()
    num = Member.objects.all()
    for i in num :
#캐시에 데이터가 있을 경우
        if r.exists(i.member_id):
            print("if enter")
            item = r.hgetall(str(i.member_id))
            member_id=item['id']
            name=item['name']
            birth=item['birth']
            print(member_id,name,birth)
            member_dict.append({
               'id': member_id,
               'name': name,
               'birth': birth
            })

#캐시에 데이터가 없을 경우
        else :
            print("else enter")

            one = Member.objects.get(member_id=str(i.member_id))
            print(one)
            member = dict()
            member[str(one.member_id)] = [one.name, one.birth]
            r.hmset(str(one.member_id),
            {'id':one.member_id, 'name':one.name, 'birth':one.birth})
            r.expire(str(one.member_id), time=30)
            item = r.hgetall(str(one.member_id))
            member_id=item['id']
            name=item['name']
            birth=item['birth']

            member_dict.append({
               'id': member_id,
               'name': name,
               'birth': birth
            })
            #jsonData = json.dumps(data_dict.decode('utf-8'), ensure_ascii=False).encode('utf-8')
#keys = r.keys(*)

    return render(request, 'search/memberList.html', {'data':member_dict} )

def goToCreate(request):
    return render(request, 'search/memberCreating.html')
   
def createMemberInfo(request):
# POST METHOD
    print("test")
    if request.method == 'POST':
        print(request.POST)
#Valid checking
        Member(
            name = request.POST.get('name'),
            birth = request.POST.get('birth'),
        ).save()
    return HttpResponseRedirect('/search/memberlist')

# GET METHOD

def goToUpdate(request):
    print(request.GET.get('member_id'))
    data = Member.objects.get(member_id=request.GET.get('member_id'))
    print(data.member_id)
    print(data.name)
    print(data.birth)
    return render(request, 'search/memberUpdating.html', {'datas':data})


def updateMemberInfo(request):
    if request.method == 'POST':
        print(request.POST.get('member_id'))
        print(request.POST.get('name'))
        print(request.POST.get('birth'))
        r = redis.StrictRedis(host='10.113.79.189', port=6379, db=1, charset="utf-8", decode_responses=True)
        if r.exists(request.POST.get('member_id')):
            r.delete(request.POST.get('member_id'))
#Valid checking
        someones = Member.objects.get(member_id=request.POST.get('member_id'))
        someones.name = request.POST.get('name')
        someones.birth = request.POST.get('birth')
        someones.save()
    return HttpResponseRedirect('/search/memberlist')

# GET METHOD

def deleteMemberInfo(request):
    if request.method == 'GET':
        print(request.GET.get('member_id'))
        print(request.GET.get('name'))
        print(request.GET.get('birth'))
#Valid checking
        someones = Member.objects.get(member_id=request.GET.get('member_id'))
        someones.delete()
    return HttpResponseRedirect('/search/memberlist')
