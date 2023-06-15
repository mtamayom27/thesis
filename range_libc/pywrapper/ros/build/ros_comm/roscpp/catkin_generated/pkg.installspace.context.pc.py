# generated from catkin/cmake/template/pkg.context.pc.in
CATKIN_PACKAGE_PREFIX = ""
PROJECT_PKG_CONFIG_INCLUDE_DIRS = "${prefix}/include;/usr/local/include".split(';') if "${prefix}/include;/usr/local/include" != "" else []
PROJECT_CATKIN_DEPENDS = "cpp_common;message_runtime;rosconsole;roscpp_serialization;roscpp_traits;rosgraph_msgs;rostime;std_msgs;xmlrpcpp".replace(';', ' ')
PKG_CONFIG_LIBRARIES_WITH_PREFIX = "-lroscpp;/usr/local/lib/libboost_chrono-mt.dylib;/usr/local/lib/libboost_filesystem-mt.dylib;/usr/local/lib/libboost_system-mt.dylib".split(';') if "-lroscpp;/usr/local/lib/libboost_chrono-mt.dylib;/usr/local/lib/libboost_filesystem-mt.dylib;/usr/local/lib/libboost_system-mt.dylib" != "" else []
PROJECT_NAME = "roscpp"
PROJECT_SPACE_DIR = "/usr/local"
PROJECT_VERSION = "1.14.13"
