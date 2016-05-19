#!/usr/bin/env ruby

puts 'compiling...'
`cd ..; ./gradlew --daemon clean shadowJar && cd scripts/;`

(0..19).each { |i|
  puts "java -cp ../build/libs/jgroups-tester-1.0-SNAPSHOT-all.jar EventTesterKt  > localhost#{i}.txt 2>&1 &\n"
  `java -cp ../build/libs/jgroups-tester-1.0-SNAPSHOT-all.jar EventTesterKt  > localhost#{i}.txt 2>&1 &`
}
