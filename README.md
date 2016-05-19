# jgroups-tester

This dummy application was created to test JGroups against EpTO. A working implementation of EpTO can be found at : [https://github.com/jocelynthode/epto-neem](https://github.com/jocelynthode/epto-neem)

## Compile & Run

If you want to compile it and run it directly from gradle, just use : `./gradlew --daemon run`

Alternatively if you want to run it not using gradle :

* To compile use `./gradlew --daemon shadowJar`. This will create a jar containing everything you need.

* If you then want to run it separately you can do : `java -cp jgroups-tester-1.0-SNAPSHOT-all.jar EventTesterKt`


## Scripts

A small script was provided to run multiple instance concurrently locally. Take a look in `scripts/`