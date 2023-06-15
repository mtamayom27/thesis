# Install script for directory: /Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/src/class_loader

# Set the install prefix
if(NOT DEFINED CMAKE_INSTALL_PREFIX)
  set(CMAKE_INSTALL_PREFIX "/usr/local")
endif()
string(REGEX REPLACE "/$" "" CMAKE_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}")

# Set the install configuration name.
if(NOT DEFINED CMAKE_INSTALL_CONFIG_NAME)
  if(BUILD_TYPE)
    string(REGEX REPLACE "^[^A-Za-z0-9_]+" ""
           CMAKE_INSTALL_CONFIG_NAME "${BUILD_TYPE}")
  else()
    set(CMAKE_INSTALL_CONFIG_NAME "")
  endif()
  message(STATUS "Install configuration: \"${CMAKE_INSTALL_CONFIG_NAME}\"")
endif()

# Set the component getting installed.
if(NOT CMAKE_INSTALL_COMPONENT)
  if(COMPONENT)
    message(STATUS "Install component: \"${COMPONENT}\"")
    set(CMAKE_INSTALL_COMPONENT "${COMPONENT}")
  else()
    set(CMAKE_INSTALL_COMPONENT)
  endif()
endif()

# Is this installation the result of a crosscompile?
if(NOT DEFINED CMAKE_CROSSCOMPILING)
  set(CMAKE_CROSSCOMPILING "FALSE")
endif()

# Set default install directory permissions.
if(NOT DEFINED CMAKE_OBJDUMP)
  set(CMAKE_OBJDUMP "/usr/bin/objdump")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/pkgconfig" TYPE FILE FILES "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/class_loader/catkin_generated/installspace/class_loader.pc")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/class_loader/cmake" TYPE FILE FILES "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/src/class_loader/cmake/class_loader-extras.cmake")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/class_loader/cmake" TYPE FILE FILES
    "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/class_loader/catkin_generated/installspace/class_loaderConfig.cmake"
    "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/class_loader/catkin_generated/installspace/class_loaderConfig-version.cmake"
    )
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/class_loader" TYPE FILE FILES "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/src/class_loader/package.xml")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib" TYPE SHARED_LIBRARY FILES "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/devel/lib/libclass_loader.dylib")
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libclass_loader.dylib" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libclass_loader.dylib")
    execute_process(COMMAND /usr/bin/install_name_tool
      -delete_rpath "/usr/local/lib"
      "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libclass_loader.dylib")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" -x "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/libclass_loader.dylib")
    endif()
  endif()
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include/class_loader" TYPE DIRECTORY FILES "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/src/class_loader/include/class_loader/")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/class_loader" TYPE PROGRAM FILES "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/src/class_loader/scripts/class_loader_headers_update.py")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for each subdirectory.
  include("/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/class_loader/test/cmake_install.cmake")

endif()

