import org.jgroups.*
import java.util.*

/**
 * This Class connects to a cluster, waits for other peers to join and then sends a number of events
 *
 * This implementation uses the SEQUENCER Channel. This uses Total Order and UDP
 *
 * @author Jocelyn Thode
 */

class EventTester : ReceiverAdapter() {

    var channel = JChannel("sequencer.xml")
    val MAX_EVENTS_SENT = 20
    val TIME_TO_WAIT = 30000L

    fun start() {
        channel.receiver = this
        channel.connect("EventCluster")
        var eventsSent = 0

        // Give time for all peers to join
        Thread.sleep(TIME_TO_WAIT)
        while(eventsSent != MAX_EVENTS_SENT) {
            channel.send(Message(null, null, "${UUID.randomUUID()}"))
            eventsSent++
            Thread.sleep(1000)
        }
        //channel.close()
    }

    override fun viewAccepted(newView: View) {
        println("** view: $newView")
    }

    override fun receive(msg: Message) {
        println("${msg.src} : ${msg.`object`}")
    }
}

fun main(args: Array<String>){
    val eventTester = EventTester()
    eventTester.start()
    while(true) Thread.sleep(500)
}
