from django.shortcuts import render, redirect, get_object_or_404
from nucypher_utils.alice import run
from nucypher_utils.doctor import run_doc
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group

from .models import Article
from .forms import ArticleForm
from nucypher_utils.stridon_data_encrypt import encrypt_data
from nucypher_utils.stridon_premium_subscription import \
    subscribe_and_grant_permission_to
from nucypher_utils.stridon_data_decrypt import decrypt_article


# Create your views here.
@login_required(login_url='/login/')
def home(request):
    stridon_user = None
    if request.user.is_authenticated:
        stridon_user = request.user
    context = {
        'stridon_user': stridon_user,
    }
    return render(request, 'stridon_app/home.html', context=context)


def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        free_user_group = Group.objects.get(name='Free Users Group')
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            free_user_group.user_set.add(user)
            free_user_group.save()
            user.save()
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'stridon_app/signup.html', {'form': form})


@login_required(login_url='/login/')
def subscribe(request):
    paid_user_group = Group.objects.get(name='Paid Users Group')
    stridon_user = None
    if request.user.is_authenticated:
        stridon_user = request.user
    if subscribe_and_grant_permission_to(stridon_user.username):
        paid_user_group.user_set.add(stridon_user)
        paid_user_group.save()
        stridon_user.save()
        context = {
            'stridon_user': stridon_user,
            'paid_group': paid_user_group,
        }
        return render(request, 'stridon_app/subscribe.html', context=context)
    else:
        raise


@login_required(login_url='/login/')
def unsubscribe(request):
    paid_user_group = Group.objects.get(name='Paid Users Group')
    stridon_user = None
    if request.user.is_authenticated:
        stridon_user = request.user
        stridon_user.groups.remove(paid_user_group)
        paid_user_group.save()
        stridon_user.save()
        context = {
            'stridon_user': stridon_user,
            'paid_group': paid_user_group,
        }
        return render(request, 'stridon_app/unsubscribe.html', context=context)


@login_required(login_url='/login/')
def add_article(request):
    stridon_user = None
    if request.user.is_authenticated:
        stridon_user = request.user
    context = {
        '': ''
    }
    if request.method == 'POST':
        form = ArticleForm(request.POST)
        if form.is_valid():
            # data souce pub key naming convention:
            # author_name-article_title-article_id-datasource-pubkey.msgpack
            article_instance = form.save(commit=False)
            article_instance.author = stridon_user

            DATASOURCE_FILENAME = f"\
{article_instance.author.username}-\
{article_instance.title}-\
datasource-pubkey.msgpack"

            article_instance.plain_content = article_instance.content
            article_instance.content = encrypt_data(
                plain_text=article_instance.content,
                datasource_filename=DATASOURCE_FILENAME
            )
            article_instance.save()
            return redirect('view-article', article_id=article_instance.id)
            # return redirect('home')
    else:
        form = ArticleForm()
        context = {
            'form': form,
            'stridon_user': stridon_user,
        }
    return render(request, 'stridon_app/add_article.html', context=context)


@login_required(login_url='/login/')
def view_article(request, article_id):
    stridon_user = None
    if request.user.is_authenticated:
        stridon_user = request.user
    article = get_object_or_404(Article, id=article_id)
    if not article.is_premium_content\
            or stridon_user.has_perm('stridon_app.can_view_paid_articles'):

        pt_article_content, failed = decrypt_article(article)
        context = {
            'stridon_user': stridon_user,
            'article': article,
            'pt_article_content': pt_article_content,
            'failed': failed,
        }
        return render(
            request,
            'stridon_app/view_article.html',
            context=context
        )

    else:
        context = {
            'stridon_user': stridon_user,
        }
        return render(
            request,
            'stridon_app/premium_members_only.html',
            context=context,
        )


@login_required(login_url='/login/')
def plain_view_article(request, article_id):
    stridon_user = None
    if request.user.is_authenticated:
        stridon_user = request.user
    article = get_object_or_404(Article, id=article_id)
    context = {
        'stridon_user': stridon_user,
        'article': article,
    }
    return render(
        request,
        'stridon_app/pt_view_article.html',
        context=context
    )


@login_required(login_url='/login/')
def list_articles(request):
    paid_articles_list = Article.objects.filter(is_premium_content=True)
    free_articles_list = Article.objects.filter(is_premium_content=False)
    stridon_user = None
    if request.user.is_authenticated:
        stridon_user = request.user
    context = {
        'paid_articles_list': paid_articles_list,
        'free_articles_list': free_articles_list,
        'stridon_user': stridon_user,
    }
    return render(request, 'stridon_app/list_articles.html', context=context)


def alice(request):
    run()
    return render(request, 'stridon_app/alice.html')


def doctor(request):
    run_doc()
    return render(request, 'stridon_app/doctor.html')
