from django.shortcuts import render

# Home Page
def homeIndex(request):
	context = {}
	template_name = 'home/index.html'
	return render(request,template_name,context)

