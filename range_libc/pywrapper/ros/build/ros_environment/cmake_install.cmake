# Install script for directory: /Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/src/ros_environment

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
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/pkgconfig" TYPE FILE FILES "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/ros_environment/catkin_generated/installspace/ros_environment.pc")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/ros_environment/cmake" TYPE FILE FILES
    "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/ros_environment/catkin_generated/installspace/ros_environmentConfig.cmake"
    "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/ros_environment/catkin_generated/installspace/ros_environmentConfig-version.cmake"
    )
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/ros_environment" TYPE FILE FILES "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/src/ros_environment/package.xml")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/etc/catkin/profile.d" TYPE FILE FILES "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/ros_environment/catkin_generated/installspace/1.ros_distro.sh")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/ros_environment/catkin_env_hook" TYPE FILE FILES "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/ros_environment/catkin_generated/installspace/1.ros_distro.sh")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/etc/catkin/profile.d" TYPE FILE FILES "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/ros_environment/catkin_generated/installspace/1.ros_etc_dir.sh")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/ros_environment/catkin_env_hook" TYPE FILE FILES "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/ros_environment/catkin_generated/installspace/1.ros_etc_dir.sh")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/etc/catkin/profile.d" TYPE FILE FILES "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/ros_environment/catkin_generated/installspace/1.ros_package_path.sh")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/ros_environment/catkin_env_hook" TYPE FILE FILES "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/ros_environment/catkin_generated/installspace/1.ros_package_path.sh")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/etc/catkin/profile.d" TYPE FILE FILES "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/ros_environment/catkin_generated/installspace/1.ros_version.sh")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/ros_environment/catkin_env_hook" TYPE FILE FILES "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/ros_environment/catkin_generated/installspace/1.ros_version.sh")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/etc/catkin/profile.d" TYPE FILE FILES "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/ros_environment/catkin_generated/installspace/1.ros_python_version.sh")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/ros_environment/catkin_env_hook" TYPE FILE FILES "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/ros_environment/catkin_generated/installspace/1.ros_python_version.sh")
endif()

