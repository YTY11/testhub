from rest_framework.routers import DefaultRouter
from .views import JenkinsBuildRecordViewSet

router = DefaultRouter()
router.register(r'jenkins-builds', JenkinsBuildRecordViewSet, basename='jenkins-build')

urlpatterns = router.urls