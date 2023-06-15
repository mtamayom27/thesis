# Install script for directory: /Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/src/ros_comm/rosout

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
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/pkgconfig" TYPE FILE FILES "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/ros_comm/rosout/catkin_generated/installspace/rosout.pc")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/rosout/cmake" TYPE FILE FILES
    "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/ros_comm/rosout/catkin_generated/installspace/rosoutConfig.cmake"
    "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/ros_comm/rosout/catkin_generated/installspace/rosoutConfig-version.cmake"
    )
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/share/rosout" TYPE FILE FILES "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/src/ros_comm/rosout/package.xml")
endif()

if(CMAKE_INSTALL_COMPONENT STREQUAL "Unspecified" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/lib/rosout" TYPE EXECUTABLE FILES "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/devel/lib/rosout/rosout")
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/rosout/rosout" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/rosout/rosout")
    execute_process(COMMAND /usr/bin/install_name_tool
      -delete_rpath "/Users/anna/Documents/TUM/Thesis/ba-bio-inspired-navigation-main/range_libc/pywrapper/ros/build/devel/lib"
      -delete_rpath "/usr/local/lib"
      "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/rosout/rosout")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" -u -r "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/lib/rosout/rosout")
    endif()
  endif()
endif()

