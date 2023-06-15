# Install script for directory: /Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/src/ros_comm/roslaunch

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
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/pkgconfig" TYPE FILE FILES "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/ros_comm/roslaunch/catkin_generated/installspace/roslaunch.pc")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/roslaunch/cmake" TYPE FILE FILES "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/ros_comm/roslaunch/catkin_generated/installspace/roslaunch-extras.cmake")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/roslaunch/cmake" TYPE FILE FILES
    "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/ros_comm/roslaunch/catkin_generated/installspace/roslaunchConfig.cmake"
    "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/ros_comm/roslaunch/catkin_generated/installspace/roslaunchConfig-version.cmake"
    )
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/roslaunch" TYPE FILE FILES "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/src/ros_comm/roslaunch/package.xml")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/etc/catkin/profile.d" TYPE FILE FILES "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/src/ros_comm/roslaunch/env-hooks/10.roslaunch.sh")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/roslaunch/catkin_env_hook" TYPE FILE FILES "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/src/ros_comm/roslaunch/env-hooks/10.roslaunch.sh")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  include("/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/ros_comm/roslaunch/catkin_generated/safe_execute_install.cmake")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/etc/ros" TYPE FILE FILES "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/src/ros_comm/roslaunch/resources/roscore.xml")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/roslaunch" TYPE DIRECTORY FILES "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/src/ros_comm/roslaunch/resources")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/roslaunch/scripts" TYPE PROGRAM FILES "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/ros_comm/roslaunch/catkin_generated/installspace/roslaunch-check")
endif()

