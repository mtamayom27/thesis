# generated from catkin/cmake/template/pkg.context.pc.in
CATKIN_PACKAGE_PREFIX = ""
PROJECT_PKG_CONFIG_INCLUDE_DIRS = "${prefix}/include;/usr/local/include".split(';') if "${prefix}/include;/usr/local/include" != "" else []
PROJECT_CATKIN_DEPENDS = "pluginlib;roslz4".replace(';', ' ')
PKG_CONFIG_LIBRARIES_WITH_PREFIX = "-lrosbag_storage;/usr/local/lib/libconsole_bridge.1.0.dylib;/usr/local/lib/libboost_date_time-mt.dylib;/usr/local/lib/libboost_filesystem-mt.dylib;/usr/local/lib/libboost_program_options-mt.dylib;/usr/local/lib/libboost_regex-mt.dylib".split(';') if "-lrosbag_storage;/usr/local/lib/libconsole_bridge.1.0.dylib;/usr/local/lib/libboost_date_time-mt.dylib;/usr/local/lib/libboost_filesystem-mt.dylib;/usr/local/lib/libboost_program_options-mt.dylib;/usr/local/lib/libboost_regex-mt.dylib" != "" else []
PROJECT_NAME = "rosbag_storage"
PROJECT_SPACE_DIR = "/usr/local"
PROJECT_VERSION = "1.14.13"
